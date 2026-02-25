import { App, TFolder, TFile } from 'obsidian';
import { StellaModal, FileSelectCallbacks } from './base';

interface FileSelectorConfig {
    title: string;
    directoryPath: string;
    fileExtension?: string;
    emptyMessage?: string;
    notFoundMessage?: string;
    previewHint?: string;
}

// Generic file selector modal for system prompts, mental models, etc.
export class FileSelectorModal extends StellaModal {
    private directoryPath: string;
    private fileExtension: string;
    private callbacks: FileSelectCallbacks;
    private emptyMessage: string;
    private notFoundMessage: string;
    private previewHint: string;
    private matchedFiles: TFile[] = [];
    private selectedIndex = 0;
    private previewVisible = false;

    constructor(app: App, config: FileSelectorConfig, callbacks: FileSelectCallbacks) {
        super(app, { title: config.title });
        // Normalize: strip trailing slashes
        this.directoryPath = config.directoryPath.replace(/\/+$/, '');
        this.fileExtension = config.fileExtension || '.md';
        this.callbacks = callbacks;
        this.emptyMessage = config.emptyMessage || `No ${this.fileExtension} files found.`;
        this.notFoundMessage = config.notFoundMessage || 'Directory not found.';
        this.previewHint = config.previewHint || 'Select a file and press → to preview';
    }

    protected async buildContent(): Promise<void> {
        if (!this.directoryPath) {
            this.contentEl.createEl('p', {
                text: 'Directory path not configured. Please check settings.'
            });
            return;
        }

        try {
            // Look up the folder in the vault's file tree
            const abstractFile = this.app.vault.getAbstractFileByPath(this.directoryPath);
            if (!(abstractFile instanceof TFolder)) {
                this.contentEl.createEl('p', {
                    text: `${this.notFoundMessage}: ${this.directoryPath}`
                });
                return;
            }

            // Get direct children that match our extension
            this.matchedFiles = abstractFile.children
                .filter((child): child is TFile =>
                    child instanceof TFile && child.name.endsWith(this.fileExtension)
                )
                .sort((a, b) => a.name.localeCompare(b.name));

            if (this.matchedFiles.length === 0) {
                this.contentEl.createEl('p', { text: this.emptyMessage });
                return;
            }

            this.buildFileList();
        } catch (error) {
            this.contentEl.createEl('p', {
                text: `Error reading directory: ${error}`
            });
        }
    }

    private buildFileList(): void {
        const { leftPanel, previewContent } = this.createTwoPanelLayout();
        previewContent.textContent = this.previewHint;

        const fileList = leftPanel.createDiv({ cls: 'stella-system-prompts-list' });
        const items: HTMLElement[] = [];

        this.matchedFiles.forEach((file, index) => {
            const fileItem = fileList.createDiv({ cls: 'stella-system-prompt-item' });
            items.push(fileItem);

            const titleEl = fileItem.createDiv({ cls: 'stella-system-prompt-title' });
            titleEl.textContent = file.basename;

            fileItem.addEventListener('click', () => {
                this.selectFile(index);
            });

            fileItem.addEventListener('dblclick', () => {
                this.confirmSelection(index);
            });
        });

        this.fixListHeight(fileList);

        // Setup keyboard navigation
        this.setupKeyboardNavigation(
            items,
            (index) => this.confirmSelection(index),
            {
                onPreview: (index) => this.showPreview(index, previewContent),
                onEscape: () => {
                    if (this.previewVisible) {
                        this.hidePreview(previewContent);
                    } else {
                        this.close();
                    }
                }
            }
        );
    }

    private selectFile(index: number): void {
        const items = this.contentEl.querySelectorAll('.stella-system-prompt-item');
        items[this.selectedIndex]?.classList.remove('selected');
        this.selectedIndex = index;
        items[this.selectedIndex]?.classList.add('selected');
    }

    private async confirmSelection(index: number): Promise<void> {
        const file = this.matchedFiles[index];
        await this.callbacks.onSelect(file.path, file.name);
        this.close();
        this.callbacks.onClose?.();
    }

    private async showPreview(index: number, previewContent: HTMLElement): Promise<void> {
        try {
            const file = this.matchedFiles[index];
            const content = await this.app.vault.cachedRead(file);

            previewContent.empty();
            previewContent.createEl('h4', { text: file.basename });
            previewContent.createEl('pre', {
                cls: 'stella-preview-text',
                text: content.substring(0, 1000) + (content.length > 1000 ? '...' : '')
            });

            this.previewVisible = true;
            this.modalEl.style.width = '700px';
        } catch (error) {
            previewContent.textContent = `Error loading preview: ${error}`;
        }
    }

    private hidePreview(previewContent: HTMLElement): void {
        previewContent.textContent = this.previewHint;
        this.previewVisible = false;
        this.modalEl.style.width = '400px';
    }
}

// Convenience factory functions
export function createSystemPromptModal(
    app: App,
    directoryPath: string,
    callbacks: FileSelectCallbacks
): FileSelectorModal {
    return new FileSelectorModal(app, {
        title: 'Select System Prompt',
        directoryPath,
        fileExtension: '.md',
        emptyMessage: 'No .md files found in SystemPrompts directory.',
        notFoundMessage: 'System prompts directory not found',
        previewHint: 'Select a system prompt and press → to preview'
    }, callbacks);
}

export function createMentalModelModal(
    app: App,
    directoryPath: string,
    callbacks: FileSelectCallbacks
): FileSelectorModal {
    return new FileSelectorModal(app, {
        title: 'Select Mental Model',
        directoryPath,
        fileExtension: '.md',
        emptyMessage: 'No .md files found in MentalModels directory.',
        notFoundMessage: 'Mental models directory not found',
        previewHint: 'Select a mental model and press → to preview'
    }, callbacks);
}
