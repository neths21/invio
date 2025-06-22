// Main JavaScript file for AI Inventory Tracker

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Toggle sidebar
    const menuToggle = document.getElementById('menu-toggle');
    const wrapper = document.getElementById('wrapper');
    
    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            wrapper.classList.toggle('toggled');
        });
    }
    
    // Handle responsive sidebar
    function checkWindowSize() {
        if (window.innerWidth < 992) {
            wrapper.classList.remove('toggled');
        } else {
            wrapper.classList.add('toggled');
        }
    }
    
    // Initialize sidebar state
    checkWindowSize();
    
    // Check window size on resize
    window.addEventListener('resize', checkWindowSize);
    
    // Handle notification read status
    const notificationButtons = document.querySelectorAll('.mark-read-btn');
    if (notificationButtons) {
        notificationButtons.forEach(button => {
            button.addEventListener('click', function() {
                const notificationId = this.getAttribute('data-id');
                markNotificationAsRead(notificationId);
            });
        });
    }
    
    // Handle dynamic form fields for purchase orders
    const addItemButton = document.getElementById('add-item-btn');
    if (addItemButton) {
        addItemButton.addEventListener('click', function() {
            addItemRow();
        });
    }
    
    // Handle product selection in transaction form
    const productSelect = document.getElementById('product_id');
    if (productSelect) {
        productSelect.addEventListener('change', function() {
            updateProductInfo(this.value);
        });
    }
    
    // Handle date range picker if exists
    const dateRangePicker = document.getElementById('date-range');
    if (dateRangePicker) {
        // This would be implemented if a date range picker library is added
    }
    
    // Fix modal jittering and multiple popups issue
    const modals = document.querySelectorAll('.modal');
    let activeModal = null;

    modals.forEach(modal => {
        modal.addEventListener('show.bs.modal', function (event) {
            // Close any currently active modal
            if (activeModal && activeModal !== modal) {
                bootstrap.Modal.getInstance(activeModal).hide();
            }

            activeModal = modal;
            document.body.style.overflow = 'hidden';

            // Disable mouse events on the body to prevent interference
            document.body.style.pointerEvents = 'none';
        });

        modal.addEventListener('hidden.bs.modal', function (event) {
            if (activeModal === modal) {
                activeModal = null;
            }

            document.body.style.overflow = '';

            // Re-enable mouse events on the body
            document.body.style.pointerEvents = '';
        });
    });

    // Prevent multiple modals from being triggered simultaneously
    document.querySelectorAll('[data-bs-toggle="modal"]').forEach(trigger => {
        trigger.addEventListener('click', function (event) {
            if (activeModal) {
                event.preventDefault();
                return;
            }
        });
    });
});

// Function to mark notification as read
function markNotificationAsRead(notificationId) {
    fetch('/notifications/mark_read/' + notificationId, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('notification-' + notificationId).classList.remove('unread');
            
            // Update notification counter
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                let count = parseInt(badge.textContent);
                if (count > 1) {
                    badge.textContent = count - 1;
                } else {
                    badge.remove();
                }
            }
        }
    })
    .catch(error => console.error('Error:', error));
}

// Function to add a new item row in purchase order form
function addItemRow() {
    const itemsContainer = document.getElementById('items-container');
    const itemCount = itemsContainer.querySelectorAll('.item-row').length;
    
    const newRow = document.createElement('div');
    newRow.className = 'row item-row mb-3';
    newRow.innerHTML = `
        <div class="col-md-5">
            <select name="items[${itemCount}][product_id]" class="form-select" required>
                <option value="">Select Product</option>
                ${document.getElementById('product-options-template').innerHTML}
            </select>
        </div>
        <div class="col-md-3">
            <input type="number" name="items[${itemCount}][quantity]" class="form-control" placeholder="Quantity" min="1" required>
        </div>
        <div class="col-md-3">
            <input type="number" name="items[${itemCount}][unit_price]" class="form-control" placeholder="Unit Price" step="0.01" min="0" required>
        </div>
        <div class="col-md-1">
            <button type="button" class="btn btn-danger remove-item-btn">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    itemsContainer.appendChild(newRow);
    
    // Add event listener to the remove button
    newRow.querySelector('.remove-item-btn').addEventListener('click', function() {
        this.closest('.item-row').remove();
    });
}

// Function to update product information in transaction form
function updateProductInfo(productId) {
    if (!productId) return;
    
    fetch('/api/products/' + productId)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const product = data.product;
                document.getElementById('current_quantity').value = product.quantity;
                document.getElementById('current_quantity_display').textContent = product.quantity;
                
                // If there's a max quantity field for "out" transactions, update it
                const maxQuantityInput = document.getElementById('max_quantity');
                if (maxQuantityInput) {
                    maxQuantityInput.value = product.quantity;
                }
            }
        })
        .catch(error => console.error('Error:', error));
}

// Additional UI/UX enhancements

// Toast Notification System
class ToastNotification {
    constructor() {
        this.createContainer();
    }
    
    createContainer() {
        // Create toast container if it doesn't exist
        if (!document.querySelector('.toast-container')) {
            const container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
    }
    
    show(message, title = 'Notification', type = 'info', duration = 5000) {
        const container = document.querySelector('.toast-container');
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.setAttribute('role', 'alert');
        
        // Set icon based on type
        let icon;
        switch (type) {
            case 'success':
                icon = '<i class="fas fa-check-circle text-success"></i>';
                break;
            case 'warning':
                icon = '<i class="fas fa-exclamation-circle text-warning"></i>';
                break;
            case 'error':
                icon = '<i class="fas fa-times-circle text-danger"></i>';
                break;
            default:
                icon = '<i class="fas fa-info-circle text-primary"></i>';
        }
        
        toast.innerHTML = `
            <div class="toast-header">
                <div class="me-2">${icon}</div>
                <strong class="me-auto">${title}</strong>
                <small>Just now</small>
                <button type="button" class="btn-close" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        // Add to container
        container.appendChild(toast);
        
        // Close button functionality
        const closeBtn = toast.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => {
            toast.classList.add('hide');
            setTimeout(() => {
                toast.remove();
            }, 300);
        });
        
        // Auto-dismiss
        setTimeout(() => {
            toast.classList.add('hide');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, duration);
    }
}

// Initialize toast notification system
const toast = new ToastNotification();

// Animated numbers for statistics
function animateValue(element, start, end, duration) {
    if (!element) return;
    
    // Check if this is a monetary value by looking at parent elements or context
    const isMonetary = element.closest('.stat-value')?.querySelector('.suffix')?.textContent.includes('$') || 
                       element.parentElement?.textContent.includes('$') || 
                       element.textContent.includes('$');
    
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const value = progress * (end - start) + start;
        
        // Format only monetary values with decimal places, integers for everything else
        if (isMonetary) {
            element.textContent = value.toFixed(2);
        } else {
            element.textContent = Math.round(value);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// Add a function to animate number changes
function animateNumberChange(element, start, end, duration = 500, isPrice = false) {
    start = parseFloat(start) || 0;
    end = parseFloat(end) || 0;
    
    if (start === end) return;
    
    const range = end - start;
    const stepTime = Math.abs(Math.floor(duration / range)) || 10;
    const startTime = new Date().getTime();
    const endTime = startTime + duration;
    
    function updateNumber() {
        const now = new Date().getTime();
        const remaining = Math.max((endTime - now) / duration, 0);
        const value = end - (remaining * range);
        
        if (isPrice) {
            element.textContent = '$' + value.toFixed(2);
        } else {
            element.textContent = Math.round(value).toString();
        }
        
        if (now >= endTime) {
            clearInterval(timer);
            element.classList.add('animate-value');
            setTimeout(() => element.classList.remove('animate-value'), 1000);
        }
    }
    
    const timer = setInterval(updateNumber, stepTime);
    updateNumber();
}

// Add input group focus effects
document.addEventListener('DOMContentLoaded', function() {
    const inputElements = document.querySelectorAll('.form-control, .form-select');
    inputElements.forEach(element => {
        element.addEventListener('focus', function() {
            const inputGroup = this.closest('.input-group');
            if (inputGroup) inputGroup.classList.add('input-group-focus');
        });
        element.addEventListener('blur', function() {
            const inputGroup = this.closest('.input-group');
            if (inputGroup) inputGroup.classList.remove('input-group-focus');
        });
    });
    
    // Add keyboard shortcut badges
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => {
        button.setAttribute('data-shortcut', 'Alt+S');
    });
    
    const cancelButtons = document.querySelectorAll('a.btn-outline-secondary');
    cancelButtons.forEach(button => {
        if (button.textContent.includes('Cancel')) {
            button.setAttribute('data-shortcut', 'Alt+C');
        }
    });
});

// Auto initialize any elements with data-animate-value attribute
document.addEventListener('DOMContentLoaded', function() {
    // Toggle sidebar in mobile view when the toggle button is clicked
    const menuToggle = document.getElementById('menu-toggle');
    const wrapper = document.getElementById('wrapper');
    
    if (menuToggle && wrapper) {
        menuToggle.addEventListener('click', function() {
            wrapper.classList.toggle('toggled');
        });
    }      // Animate stats on page load
    const statsElements = document.querySelectorAll('.stat-value');
    if (statsElements.length > 0) {
        statsElements.forEach(element => {
            // Look for a .number-value element inside the stat-value
            const numberElement = element.querySelector('.number-value');
            
            // Check if this is a monetary value (contains $ or has a monetary suffix)
            const isMonetary = element.textContent.includes('$') || 
                              (element.querySelector('.suffix') && 
                               ['K', 'M', 'B'].some(s => element.querySelector('.suffix').textContent.includes(s)));
            
            if (numberElement) {
                // Only animate the number part, not the suffix
                const value = parseFloat(numberElement.textContent.replace(/[^0-9.]/g, ''), 10);
                numberElement.textContent = '0';
                setTimeout(() => {
                    // Store if this is monetary for the animation function
                    numberElement.dataset.isMonetary = isMonetary ? 'true' : 'false';
                    animateValue(numberElement, 0, value, 1000);
                }, 300);
            } else {
                // Fall back to the original animation if there's no .number-value element
                const rawText = element.textContent.trim();
                const hasMoneySymbol = rawText.includes('$');
                const value = parseFloat(rawText.replace(/[^0-9.]/g, ''), 10);
                
                element.textContent = hasMoneySymbol ? '$0' : '0';
                setTimeout(() => {
                    // Store if this is monetary for the animation function
                    element.dataset.isMonetary = hasMoneySymbol ? 'true' : 'false';
                    animateValue(element, 0, value, 1000);
                }, 300);
            }
        });
    }
    
    // Handle flash messages with toast notifications
    const flashMessages = document.querySelectorAll('.alert');
    if (flashMessages.length > 0) {
        flashMessages.forEach(message => {
            const text = message.textContent.trim();
            const type = message.classList.contains('alert-success') ? 'success' : 
                        message.classList.contains('alert-warning') ? 'warning' : 
                        message.classList.contains('alert-danger') ? 'error' : 'info';
            
            // Remove the default alert and show as toast
            message.style.display = 'none';
            toast.show(text, 'System Message', type);
        });
    }
    
    // Add keyboard shortcut hints to certain elements
    const addButtons = document.querySelectorAll('a.btn-primary:not(.has-shortcut)');
    if (addButtons.length > 0) {
        addButtons.forEach((button, index) => {
            if (index === 0 && button.textContent.includes('Add')) {
                button.setAttribute('data-bs-toggle', 'tooltip');
                button.setAttribute('data-bs-placement', 'bottom');
                button.setAttribute('title', 'Shortcut: Alt+N');
                button.classList.add('has-shortcut');
                
                // Re-initialize tooltips
                new bootstrap.Tooltip(button);
            }
        });
    }
    
    // Handle keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Alt+N for new/add
        if (e.altKey && e.key === 'n') {
            const addButton = document.querySelector('a.btn-primary:not(.disabled)');
            if (addButton) {
                e.preventDefault();
                addButton.click();
            }
        }
        
        // Alt+S for save/submit
        if (e.altKey && e.key === 's') {
            const submitButton = document.querySelector('button[type="submit"]:not(.disabled)');
            if (submitButton) {
                e.preventDefault();
                submitButton.click();
            }
        }
        
        // Alt+H for home/dashboard
        if (e.altKey && e.key === 'h') {
            const homeLink = document.querySelector('a[href="/"]');
            if (homeLink) {
                e.preventDefault();
                homeLink.click();
            }
        }
    });
});

// Function to create and manage data tables with advanced features
function initDataTable(tableId, options = {}) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    // Default options
    const defaultOptions = {
        perPage: 10,
        search: true,
        pagination: true,
        sortable: true
    };
    
    // Merge options
    const settings = {...defaultOptions, ...options};
    
    // Create table wrapper and controls
    const wrapper = document.createElement('div');
    wrapper.className = 'datatable-wrapper';
    
    // Create search input if enabled
    if (settings.search) {
        const searchContainer = document.createElement('div');
        searchContainer.className = 'datatable-search mb-3';
        searchContainer.innerHTML = `
            <div class="input-group">
                <span class="input-group-text bg-transparent border-end-0">
                    <i class="fas fa-search"></i>
                </span>
                <input type="text" class="form-control border-start-0" id="${tableId}-search" placeholder="Search...">
            </div>
        `;
        wrapper.appendChild(searchContainer);
        
        // Implement search functionality
        const searchInput = searchContainer.querySelector('input');
        searchInput.addEventListener('keyup', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
            
            updatePagination();
        });
    }
    
    // Function to update pagination
    function updatePagination() {
        if (!settings.pagination) return;
        
        // Implement pagination logic here
    }
    
    // Initialize
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(table);
    
    return {
        update: updatePagination
    };
}

// Theme toggle functionality (preparation for dark mode)
function initThemeToggle() {
    // Create toggle button
    const toggleBtn = document.createElement('div');
    toggleBtn.className = 'dark-mode-toggle';
    toggleBtn.innerHTML = '<i class="fas fa-moon"></i>';
    document.body.appendChild(toggleBtn);
    
    // Check if dark mode is enabled in localStorage
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    if (isDarkMode) {
        document.body.classList.add('dark-mode');
        toggleBtn.innerHTML = '<i class="fas fa-sun"></i>';
    }
    
    // Toggle dark mode on click
    toggleBtn.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', isDark);
        toggleBtn.innerHTML = isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
        
        // Show toast notification
        toast.show(
            isDark ? 'Dark mode enabled' : 'Light mode enabled', 
            'Theme Changed', 
            'info', 
            2000
        );
    });
}

// Call theme toggle on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    // Uncomment when ready to implement dark mode
    // initThemeToggle();
});

// Analytics data visualization helper
function createChart(elementId, config) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return null;
    
    return new Chart(ctx, config);
}

// Progress indicator for any async operations
function showProgress(message = 'Loading...') {
    const overlay = document.createElement('div');
    overlay.className = 'progress-overlay';
    overlay.innerHTML = `
        <div class="progress-spinner">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div class="mt-2">${message}</div>
        </div>
    `;
    document.body.appendChild(overlay);
    
    return {
        hide: () => {
            overlay.classList.add('fade-out');
            setTimeout(() => {
                overlay.remove();
            }, 300);
        }
    };
}

// File upload preview
function setupFileUploadPreview(inputId, previewId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    
    if (input && preview) {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.addEventListener('load', function() {
                    preview.src = reader.result;
                    preview.style.display = 'block';
                });
                reader.readAsDataURL(file);
            }
        });
    }
}

// Export data to CSV
function exportTableToCSV(tableId, filename = 'export.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.querySelectorAll('tr');
    let csv = [];
    
    for (let i = 0; i < rows.length; i++) {
        const row = [], cols = rows[i].querySelectorAll('td, th');
        
        for (let j = 0; j < cols.length; j++) {
            // Get the text content and remove any commas to avoid CSV issues
            let text = cols[j].textContent.replace(/,/g, ';').trim();
            // If it's a cell with just an icon or action buttons, skip it
            if (cols[j].querySelector('.btn-group') || (text === '' && cols[j].querySelector('i'))) {
                continue;
            }
            row.push('"' + text + '"');
        }
        
        csv.push(row.join(','));
    }
    
    // Download CSV file
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    
    // Create download link and click it
    const link = document.createElement('a');
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// ---------------
// Camera with Preview + Retry + Barcode Decode Logic
// ---------------

let cameraStream = null;

document.addEventListener('DOMContentLoaded', function() {
  const openCameraBtn   = document.getElementById('open-camera-btn');
  const cancelCameraBtn = document.getElementById('cancel-camera-btn');
  const captureBtn      = document.getElementById('capture-btn');
  const retryBtn        = document.getElementById('retry-btn');
  const useImageBtn     = document.getElementById('use-image-btn');

  const cameraVideo     = document.getElementById('cameraVideo');
  const previewImage    = document.getElementById('previewImage');
  const barcodeInput    = document.getElementById('barcodeImageData');
  const skuInput        = document.getElementById('sku-input');
  const cameraModalEl   = document.getElementById('cameraModal');

  let cameraModal = null;

  // 1) Open modal & start camera
  if (openCameraBtn) {
    openCameraBtn.addEventListener('click', function() {
      // Lazy‐create Bootstrap modal instance
      if (!cameraModal) {
        cameraModal = new bootstrap.Modal(cameraModalEl, {
          backdrop: 'static',
          keyboard: false
        });
      }
      cameraModal.show();
      startCameraStream();
    });
  }

  // 2) Cancel: stop everything and close
  if (cancelCameraBtn) {
    cancelCameraBtn.addEventListener('click', function() {
      stopCameraStream();
      resetModalToLive();
      if (cameraModal) {
        cameraModal.hide();
      }
    });
  }

  // 3) Capture: show a preview instead of live video, then decode
  if (captureBtn) {
    captureBtn.addEventListener('click', function() {
      if (!cameraStream) {
        alert('Camera not running.');
        return;
      }

      // Draw the current frame onto a hidden canvas
      const canvas = document.createElement('canvas');
      canvas.width  = cameraVideo.videoWidth;
      canvas.height = cameraVideo.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(cameraVideo, 0, 0, canvas.width, canvas.height);

      // Convert to Base64 string
      const dataURL = canvas.toDataURL('image/png');

      // Show preview
      previewImage.src = dataURL;
      previewImage.style.display = 'block';
      cameraVideo.style.display = 'none';

      // Stop the camera immediately
      stopCameraStream();

      // Swap buttons: hide Capture, show Retry & Use Image
      captureBtn.style.display = 'none';
      retryBtn.style.display   = 'inline-block';
      useImageBtn.style.display = 'inline-block';

      // Store dataURL in the img’s data attribute
      previewImage.dataset.capturedData = dataURL;

      // Attempt to decode the barcode with QuaggaJS
      decodeBarcodeFromDataURL(dataURL);
    });
  }

  // 4) Retry: go back to live feed
  if (retryBtn) {
    retryBtn.addEventListener('click', function() {
      resetModalToLive();
      startCameraStream();
    });
  }

  // 5) Use Image: write Base64 into hidden <input> and close
  if (useImageBtn) {
    useImageBtn.addEventListener('click', function() {
      const dataURL = previewImage.dataset.capturedData || '';
      if (dataURL) {
        barcodeInput.value = dataURL;
      }
      // At this point, skuInput.value should already be set if decode succeeded
      resetModalToLive();
      if (cameraModal) {
        cameraModal.hide();
      }
    });
  }

  // 6) If user clicks the “X” in the header or outside, clean up
  cameraModalEl.addEventListener('hidden.bs.modal', function() {
    stopCameraStream();
    resetModalToLive();
  });


  // === Helper Functions ===

  function startCameraStream() {
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      .then(function(stream) {
        cameraStream                = stream;
        cameraVideo.srcObject       = stream;
        cameraVideo.style.display   = 'block';
        previewImage.style.display  = 'none';

        captureBtn.style.display    = 'inline-block';
        retryBtn.style.display      = 'none';
        useImageBtn.style.display   = 'none';

        cameraVideo.play();
      })
      .catch(function(err) {
        if (cameraModal) cameraModal.hide();
        alert('Unable to access camera:\n' + err.message);
      });
  }

  function stopCameraStream() {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      cameraStream = null;
    }
    if (cameraVideo && cameraVideo.srcObject) {
      cameraVideo.srcObject = null;
    }
  }

  function resetModalToLive() {
    previewImage.style.display = 'none';
    previewImage.removeAttribute('src');
    delete previewImage.dataset.capturedData;

    cameraVideo.style.display = 'none';

    captureBtn.style.display   = 'inline-block';
    retryBtn.style.display     = 'none';
    useImageBtn.style.display  = 'none';
  }

function decodeBarcodeFromDataURL(dataURL) {
  console.log("▶ decodeBarcodeFromDataURL called with dataURL length:", dataURL.length);
  Quagga.decodeSingle({
    src: dataURL,
    numOfWorkers: 0,
    locate: true,
    inputStream: { size: 800 },
    locator: { patchSize: "medium", halfSample: false },
    decoder: { readers: ["code_128_reader"] }
  }, function(result) {
    console.log("🔍 Quagga callback →", result);
    if (result && result.codeResult && result.codeResult.code) {
      const decoded = result.codeResult.code.trim();
      console.log("✔ Quagga decoded:", decoded);
      skuInput.value = decoded;
    } else {
      console.log("✖ No barcode detected by Quagga.");
    }
  });
}
});

document.addEventListener('DOMContentLoaded', () => {
  const data      = window.mlResults || [];
  const names     = data.map(r => r.product_name);
  const daysLeft  = data.map(r => r.predicted_days_until_reorder);
  const immediate = data.filter(r => r.predicted_days_until_reorder === 0).length;
  const safe      = data.length - immediate;
  const popCounts = [1,2,3].map(i => data.filter(r => r.popularity_index === i).length);

  // Popularity small bar
  const popCtx = document.getElementById('popularityBarChartSmall');
  if (popCtx) new Chart(popCtx, {
    type: 'bar',
    data: {
      labels: ['Index 1','Index 2','Index 3'],
      datasets: [{ data: popCounts, backgroundColor: ['#dc3545','#17a2b8','#28a745'] }]
    },
    options: { responsive: true, plugins:{ legend:{display:false} }, scales:{ y:{beginAtZero:true,stepSize:1} } }
  });

  // Days until reorder small bar
  const barCtx = document.getElementById('barChartSmall');
  if (barCtx) new Chart(barCtx, {
    type: 'bar',
    data: {
      labels: names,
      datasets:[{ label:'Days', data: daysLeft, backgroundColor:'rgba(255,193,7,0.7)' }]
    },
    options:{ responsive:true, plugins:{ legend:{display:false} }, scales:{ y:{beginAtZero:true} } }
  });

  // Stock health pie small
  const pieCtx = document.getElementById('pieChartSmall');
  if (pieCtx) new Chart(pieCtx, {
    type: 'pie',
    data: {
      labels:['Immediate','Safe'],
      datasets:[{ data:[immediate,safe], backgroundColor:['#dc3545','#28a745'] }]
    },
    options:{ responsive:true, plugins:{ legend:{position:'bottom'} } }
  });
});
document.addEventListener('DOMContentLoaded', () => {
  // … existing chart code …

  // Analyse button handler
  const analyseBtn = document.getElementById('analyseBtn');
  if (analyseBtn && window.analysisRunUrl) {
    analyseBtn.addEventListener('click', () => {
      analyseBtn.disabled = true;
      analyseBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Running';

      fetch(window.analysisRunUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      .then(res => {
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (data.success) {
          // refresh to load new ML results
          window.location.reload();
        } else {
          throw new Error('Analysis endpoint failed');
        }
      })
      .catch(err => {
        console.error(err);
        alert('Analysis failed. See console for details.');
        analyseBtn.disabled = false;
        analyseBtn.innerHTML = '<i class="fas fa-cogs me-1"></i> Analyse';
      });
    });
  }
});
document.addEventListener('DOMContentLoaded', () => {
  const emailBtn = document.getElementById('emailBtn');
  if (emailBtn && window.analysisEmailUrl) {
    emailBtn.addEventListener('click', () => {
      emailBtn.disabled = true;
      emailBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Sending';

      fetch(window.analysisEmailUrl, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            alert('Report emailed to all users!');
          } else {
            throw new Error(data.error || 'Unknown error');
          }
        })
        .catch(err => {
          console.error(err);
          alert('Failed to send email. See console for details.');
        })
        .finally(() => {
          emailBtn.disabled = false;
          emailBtn.innerHTML = '<i class="fas fa-envelope me-1"></i> Email Report';
        });
    });
  }
});

