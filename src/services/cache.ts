interface CacheItem {
    data: any;
    timestamp: number;
    ttl: number;
}

// Client-side Cache Manager
export class CacheManager {
    private cache: Map<string, CacheItem> = new Map();
    private readonly DEFAULT_TTL = 3600000; // 1 hour in milliseconds

    constructor() {
        this.loadFromLocalStorage();
        // Clean expired entries every 5 minutes
        setInterval(() => this.cleanExpiredEntries(), 300000);
    }

    set(key: string, data: any, ttlMs: number = this.DEFAULT_TTL): void {
        const item: CacheItem = {
            data: JSON.parse(JSON.stringify(data)), // Deep clone to avoid references
            timestamp: Date.now(),
            ttl: ttlMs
        };

        this.cache.set(key, item);

        // Store in localStorage for persistence (with size limit)
        try {
            if (this.getDataSize(data) < 100000) { // 100KB limit for localStorage
                localStorage.setItem(`stella_cache_${key}`, JSON.stringify(item));
            }
        } catch (error) {
            console.warn('Failed to persist cache item to localStorage:', error);
        }
    }

    get(key: string): any | null {
        const item = this.cache.get(key);
        if (!item) return null;

        const now = Date.now();
        if (now - item.timestamp > item.ttl) {
            this.delete(key);
            return null;
        }

        return item.data;
    }

    delete(key: string): void {
        this.cache.delete(key);
        localStorage.removeItem(`stella_cache_${key}`);
    }

    has(key: string): boolean {
        const item = this.cache.get(key);
        if (!item) return false;

        const now = Date.now();
        if (now - item.timestamp > item.ttl) {
            this.delete(key);
            return false;
        }

        return true;
    }

    clear(): void {
        this.cache.clear();

        const keysToRemove: string[] = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('stella_cache_')) {
                keysToRemove.push(key);
            }
        }
        keysToRemove.forEach(key => localStorage.removeItem(key));
    }

    private loadFromLocalStorage(): void {
        try {
            const now = Date.now();
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('stella_cache_')) {
                    const rawData = localStorage.getItem(key);
                    if (rawData) {
                        const item = JSON.parse(rawData);
                        const cacheKey = key.replace('stella_cache_', '');

                        if (now - item.timestamp <= item.ttl) {
                            this.cache.set(cacheKey, item);
                        } else {
                            localStorage.removeItem(key);
                        }
                    }
                }
            }
        } catch (error) {
            console.warn('Failed to load cache from localStorage:', error);
        }
    }

    private cleanExpiredEntries(): void {
        const now = Date.now();
        const expiredKeys: string[] = [];

        this.cache.forEach((item, key) => {
            if (now - item.timestamp > item.ttl) {
                expiredKeys.push(key);
            }
        });

        expiredKeys.forEach(key => this.delete(key));
    }

    private getDataSize(data: any): number {
        return new Blob([JSON.stringify(data)]).size;
    }

    // Cache key generators for common use cases
    static modelListKey(provider: string): string {
        return `models_${provider}`;
    }

    static conversationMetaKey(): string {
        return 'conversation_metadata';
    }

    static systemPromptsKey(): string {
        return 'system_prompts_list';
    }

    static apiResponseKey(provider: string, modelName: string): string {
        return `api_response_${provider}_${modelName}`;
    }

    // Cache invalidation methods
    invalidateProviderCache(provider: string): void {
        const modelKey = CacheManager.modelListKey(provider);
        this.delete(modelKey);
    }

    invalidateAllModels(): void {
        const providers = ['openai', 'anthropic', 'google', 'ollama', 'lmstudio'];
        providers.forEach(provider => this.invalidateProviderCache(provider));
    }

    invalidateConversationData(): void {
        this.delete(CacheManager.conversationMetaKey());
    }

    // Get cache statistics
    getCacheStats(): { totalItems: number; totalSize: number; providers: string[] } {
        let totalSize = 0;
        const providers = new Set<string>();

        this.cache.forEach((item, key) => {
            totalSize += this.getDataSize(item.data);
            if (key.startsWith('models_')) {
                providers.add(key.replace('models_', ''));
            }
        });

        return {
            totalItems: this.cache.size,
            totalSize,
            providers: Array.from(providers)
        };
    }
}
