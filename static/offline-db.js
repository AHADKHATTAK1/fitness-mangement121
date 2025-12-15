// Offline Database using IndexedDB
const DB_NAME = 'GymManagerOfflineDB';
const DB_VERSION = 1;
let db;

// Initialize IndexedDB
function initDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            db = request.result;
            resolve(db);
        };

        request.onupgradeneeded = (event) => {
            db = event.target.result;

            // Create object stores
            if (!db.objectStoreNames.contains('members')) {
                db.createObjectStore('members', { keyPath: 'id' });
            }
            if (!db.objectStoreNames.contains('pendingActions')) {
                db.createObjectStore('pendingActions', { keyPath: 'timestamp', autoIncrement: true });
            }
        };
    });
}

// Save data to IndexedDB
function saveToOfflineDB(storeName, data) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readwrite');
        const store = transaction.objectStore(storeName);
        const request = store.put(data);

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

// Get all data from store
function getAllFromDB(storeName) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([storeName], 'readonly');
        const store = transaction.objectStore(storeName);
        const request = store.getAll();

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

// Queue action for later sync
function queueAction(action) {
    return saveToOfflineDB('pendingActions', {
        action: action.type,
        data: action.data,
        timestamp: Date.now()
    });
}

// Sync pending actions when back online
async function syncPendingActions() {
    if (!navigator.onLine) return;

    try {
        const pending = await getAllFromDB('pendingActions');

        for (const action of pending) {
            // Send to server
            await fetch(action.action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(action.data)
            });

            // Remove from queue after successful sync
            const transaction = db.transaction(['pendingActions'], 'readwrite');
            const store = transaction.objectStore('pendingActions');
            store.delete(action.timestamp);
        }

        console.log('Synced all pending actions');
    } catch (error) {
        console.error('Sync failed:', error);
    }
}

// Initialize on load
window.addEventListener('load', async () => {
    await initDB();

    // Sync when coming back online
    window.addEventListener('online', syncPendingActions);
});

// Export functions for use in other scripts
window.OfflineDB = {
    save: saveToOfflineDB,
    getAll: getAllFromDB,
    queue: queueAction,
    sync: syncPendingActions
};
