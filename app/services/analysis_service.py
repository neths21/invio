import os
import uuid
from datetime import datetime, timedelta

import pandas as pd
import google.generativeai as genai
from sqlalchemy import text, func
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from dotenv import load_dotenv

from app import db
from app.models.models import MLResult

# Load your Gemini key once
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
_model = genai.GenerativeModel("gemini-1.5-flash")


class AnalysisService:
    @staticmethod
    def run_ml_analysis(days: int = 90):
        """
        1) Pull last `days` of transactions & product info
        2) Compute popularity_index & predicted_days_until_reorder
        3) Generate LLM summary per product
        4) Bulk-insert into ml_results table
        """
        run_id   = str(uuid.uuid4())
        run_date = datetime.utcnow()
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        engine   = db.engine

        # 1) Load transactions in window
        txns = pd.read_sql(
            text("""
                SELECT product_id, transaction_type, quantity, unit_price, transaction_date
                FROM inventory_transaction
                WHERE transaction_date BETWEEN :start_date AND :end_date
            """),
            engine,
            params={"start_date": start_date, "end_date": end_date}
        )

        # 2) Load product + category + supplier
        products = pd.read_sql(
            text("""
                SELECT p.id              AS product_id,
                       p.name            AS product_name,
                       c.name            AS category_name,
                       s.name            AS supplier_name,
                       p.quantity_in_stock,
                       p.reorder_level,
                       p.reorder_quantity
                FROM product p
                LEFT JOIN category c ON p.category_id = c.id
                LEFT JOIN supplier s ON p.supplier_id = s.id
            """),
            engine
        )

        # 3) Feature engineering
        grouped = (
            txns
            .groupby(["product_id","transaction_type"])["quantity"]
            .sum()
            .unstack(fill_value=0)
            .reset_index()
        )
        feat = products.merge(grouped, on="product_id", how="left").fillna(0)
        feat["stock_in"]    = feat.get("purchase", 0)
        feat["stock_out"]   = feat.get("sale", 0)
        feat["total_moved"] = feat["stock_in"] + feat["stock_out"]

        avg_price = (
            txns[txns.transaction_type=="sale"]
            .groupby("product_id")["unit_price"]
            .mean()
            .reset_index()
            .rename(columns={"unit_price":"avg_unit_price"})
        )
        feat = feat.merge(avg_price, on="product_id", how="left") \
                   .fillna({"avg_unit_price": 0})

        feat["current_stock"]          = feat["quantity_in_stock"]
        feat["avg_daily_sale"]         = (feat["stock_out"] / days).replace(0, 0.1)
        feat["days_until_reorder"]     = (
            (feat["current_stock"] - feat["reorder_level"])
            / feat["avg_daily_sale"]
        ).clip(lower=0)

        # 4) Popularity index via K-Means (3 clusters)
        pop_inputs = feat[[
            "current_stock","stock_out",
            "stock_in","total_moved",
            "avg_unit_price"
        ]]
        feat["popularity_index"] = (
            KMeans(n_clusters=3, random_state=42)
            .fit_predict(pop_inputs)
            + 1
        )

        # 5) Predict days_until_reorder with a simple regression
        X = feat[[
            "current_stock","reorder_level",
            "reorder_quantity","stock_in","stock_out"
        ]]
        y = feat["days_until_reorder"]
        feat["predicted_days_until_reorder"] = (
            LinearRegression().fit(X, y)
            .predict(X)
            .clip(min=0)
        )

        # 6) Generate AI summaries
        def _make_summary(r):
            prompt = (
                f"You are an inventory analytics assistant. Use ONLY these facts:\n"
                f"• Product: {r.product_name} (ID {r.product_id})\n"
                f"• Category: {r.category_name}\n"
                f"• Supplier: {r.supplier_name}\n"
                f"• Popularity Index (1→3): {r.popularity_index}\n"
                f"• Current Stock: {r.current_stock}\n"
                f"• Reorder Level: {r.reorder_level}\n"
                f"• Stock In (last {days}d): {r.stock_in}\n"
                f"• Stock Out (last {days}d): {r.stock_out}\n"
                f"• Predicted Days Until Reorder: {r.predicted_days_until_reorder:.1f}\n\n"
                "Write a 2–3 sentence summary. "
                "If Predicted Days Until Reorder is 0, say “This product needs restocking immediately.”"
            )
            return _model.generate_content(prompt).text.strip()

        feat["ai_summary"] = feat.apply(_make_summary, axis=1)

        # 7) Prepare ORM objects & bulk-save
        results = []
        for row in feat.itertuples(index=False):
            results.append(MLResult(
                run_id                      = run_id,
                run_date                    = run_date,
                product_id                  = int(row.product_id),
                product_name                = row.product_name,
                category_name               = row.category_name,
                supplier_name               = row.supplier_name,
                popularity_index            = int(row.popularity_index),
                predicted_days_until_reorder= float(row.predicted_days_until_reorder),
                ai_summary                  = row.ai_summary,
            ))

        db.session.bulk_save_objects(results)
        db.session.commit()

        return results

    @staticmethod
    def get_latest_results():
        """
        Fetch all MLResult rows from the most recent run_date.
        """
        latest_date = db.session.query(func.max(MLResult.run_date)).scalar()
        if not latest_date:
            return []
        return (
            MLResult.query
                    .filter(MLResult.run_date == latest_date)
                    .order_by(MLResult.product_name)
                    .all()
        )
