interface LogEntry {
    level: string;
    message: string;
    timestamp: number;
    data?: any;
}

// Asynchronous Logger Class
export class AsyncLogger {
    private logQueue: LogEntry[] = [];
    private isProcessing = false;
    private flushInterval: ReturnType<typeof setInterval> | null = null;
    private readonly FLUSH_INTERVAL = 1000; // Flush every 1 second
    private readonly MAX_QUEUE_SIZE = 100; // Force flush at 100 messages

    constructor() {
        this.startPeriodicFlush();
    }

    private startPeriodicFlush(): void {
        this.flushInterval = setInterval(() => {
            this.flushLogs();
        }, this.FLUSH_INTERVAL);
    }

    log(message: string, data?: any): void {
        this.addToQueue('log', message, data);
    }

    warn(message: string, data?: any): void {
        this.addToQueue('warn', message, data);
    }

    error(message: string, data?: any): void {
        this.addToQueue('error', message, data);
    }

    private addToQueue(level: string, message: string, data?: any): void {
        this.logQueue.push({
            level,
            message,
            timestamp: Date.now(),
            data
        });

        // Force flush if queue is getting too large
        if (this.logQueue.length >= this.MAX_QUEUE_SIZE) {
            this.flushLogs();
        }
    }

    private async flushLogs(): Promise<void> {
        if (this.isProcessing || this.logQueue.length === 0) return;

        this.isProcessing = true;
        const logsToFlush = [...this.logQueue];
        this.logQueue = [];

        // Process logs asynchronously without blocking
        setTimeout(() => {
            try {
                logsToFlush.forEach(log => {
                    const timestamp = new Date(log.timestamp).toISOString();
                    const logMessage = `[${timestamp}] ${log.message}`;

                    switch (log.level) {
                        case 'error':
                            console.error(logMessage, log.data || '');
                            break;
                        case 'warn':
                            console.warn(logMessage, log.data || '');
                            break;
                        default:
                            console.log(logMessage, log.data || '');
                            break;
                    }
                });
            } catch (error) {
                console.error('AsyncLogger flush failed:', error);
            } finally {
                this.isProcessing = false;
            }
        }, 0);
    }

    destroy(): void {
        if (this.flushInterval) {
            clearInterval(this.flushInterval);
        }
        this.flushLogs(); // Final flush
    }
}
