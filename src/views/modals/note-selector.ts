import { App, TFile, MarkdownRenderer } from 'obsidian';
import { StellaModal, NoteSelectCallbacks } from './base';

// Note selector modal for adding vault notes as context
export class NoteSelectorModal extends StellaModal {
    private callbacks: NoteSelectCallbacks;
    private files: TFile[] = [];
    private filteredFiles: TFile[] = [];
    private selectedIndex = 0;
    private previewVisible = false;
    private notesContainer: HTMLElement | null = null;
    private leftPanel: HTMLElement | null = null;
    private rightPanel: HTMLElement | null = null;
    private previewContent: HTMLElement | null = null;
    private searchInput: HTMLInputElement | null = null;

    constructor(app: App, callbacks: NoteSelectCallbacks) {
        super(app, { title: 'Add Note Context' });
        this.callbacks = callbacks;
    }

    protected buildContent(): void {
        // Search input
        this.searchInput = this.contentEl.createEl('input', {
            type: 'text',
            placeholder: 'Search notes...',
            cls: 'stella-note-search'
        }) as HTMLInputElement;

        // Create container for side-by-side layout
        const mainContainer = this.contentEl.createDiv({ cls: 'stella-modal-container' });
        this.leftPanel = mainContainer.createDiv({ cls: 'stella-modal-left-panel' });
        this.rightPanel = mainContainer.createDiv({ cls: 'stella-modal-right-panel' });

        // Create preview panel
        const previewContainer = this.rightPanel.createDiv({ cls: 'stella-preview-container' });
        this.previewContent = previewContainer.createDiv({ cls: 'stella-preview-content' });
        this.previewContent.textContent = 'Select a note and press → to preview';

        // Notes container
        this.notesContainer = this.leftPanel.createDiv({ cls: 'stella-notes-container' });

        // Get all markdown files
        this.files = this.app.vault.getMarkdownFiles();
        this.filteredFiles = this.files;

        // Initial render
        this.renderFiles();

        // Initially hide preview
        this.hidePreview();

        // Setup search
        this.searchInput.addEventListener('input', (e) => {
            const query = (e.target as HTMLInputElement).value.toLowerCase();

            if (query === '') {
                this.filteredFiles = this.files;
            } else {
                this.filteredFiles = this.files.filter(file =>
                    file.basename.toLowerCase().includes(query) ||
                    file.path.toLowerCase().includes(query)
                );
            }

            this.selectedIndex = 0;
            this.renderFiles();
        });

        // Setup keyboard navigation
        this.modalEl.addEventListener('keydown', (e) => this.handleKeydown(e));

        // Focus search input
        setTimeout(() => this.searchInput?.focus(), 50);
    }

    private renderFiles(): void {
        if (!this.notesContainer) return;

        this.notesContainer.empty();

        if (this.selectedIndex >= this.filteredFiles.length) {
            this.selectedIndex = Math.max(0, this.filteredFiles.length - 1);
        }

        // Limit to 50 results
        this.filteredFiles.slice(0, 50).forEach((file, index) => {
            const noteItem = this.notesContainer!.createDiv({ cls: 'stella-note-item' });

            const titleEl = noteItem.createDiv({ cls: 'stella-note-title' });
            titleEl.textContent = file.basename;

            const pathEl = noteItem.createDiv({ cls: 'stella-note-path' });
            pathEl.textContent = file.path;

            noteItem.addEventListener('click', () => {
                this.selectedIndex = index;
                this.updateSelection();
            });

            noteItem.addEventListener('dblclick', () => {
                this.confirmSelection();
            });

            if (index === this.selectedIndex) {
                noteItem.classList.add('selected');
            }
        });

        this.fixNotesHeight();
    }

    private updateSelection(): void {
        const items = this.notesContainer?.querySelectorAll('.stella-note-item');
        items?.forEach((item, i) => {
            item.classList.toggle('selected', i === this.selectedIndex);
        });
    }

    private async confirmSelection(): Promise<void> {
        const file = this.filteredFiles[this.selectedIndex];
        if (!file) return;

        try {
            const content = await this.app.vault.read(file);
            this.callbacks.onSelect(file.basename, content);
            this.close();
            this.callbacks.onClose?.();
        } catch (error) {
            console.error('Error reading file:', error);
        }
    }

    private async showPreview(): Promise<void> {
        const file = this.filteredFiles[this.selectedIndex];
        if (!file || !this.previewContent || !this.leftPanel || !this.rightPanel) return;

        try {
            const content = await this.app.vault.read(file);

            this.previewContent.empty();

            // Render markdown (cast to any for Component interface compatibility)
            await MarkdownRenderer.render(
                this.app,
                content.substring(0, 2000) + (content.length > 2000 ? '\n\n...' : ''),
                this.previewContent,
                file.path,
                this as any
            );

            this.rightPanel.style.display = 'block';
            this.previewVisible = true;

            this.modalEl.style.width = '60vw';
            this.modalEl.style.maxWidth = '980px';
            this.leftPanel.style.width = '50%';
            this.rightPanel.style.width = '50%';

            this.fixNotesHeight();
        } catch (error: any) {
            this.previewContent.textContent = `Error loading preview: ${error.message}`;
        }
    }

    private hidePreview(): void {
        if (!this.leftPanel || !this.rightPanel || !this.previewContent) return;

        this.rightPanel.style.display = 'none';
        this.leftPanel.style.width = '100%';
        this.previewVisible = false;

        this.modalEl.style.width = '400px';
        this.modalEl.style.maxWidth = 'none';

        this.previewContent.textContent = 'Select a note and press → to preview';

        this.fixNotesHeight();
    }

    private fixNotesHeight(): void {
        if (!this.notesContainer || !this.searchInput) return;

        setTimeout(() => {
            const modalHeight = this.modalEl.clientHeight;
            const searchInputHeight = this.searchInput!.offsetHeight + 16;
            const titleHeight = this.titleEl.offsetHeight;
            const padding = 40;

            const availableHeight = modalHeight - titleHeight - searchInputHeight - padding;
            this.notesContainer!.style.height = `${availableHeight}px`;
            this.notesContainer!.style.maxHeight = `${availableHeight}px`;
            this.notesContainer!.style.overflow = 'auto';
        }, 50);
    }

    private handleKeydown(e: KeyboardEvent): void {
        // Don't handle if typing in search
        if (e.target === this.searchInput && e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && e.key !== 'Enter' && e.key !== 'Escape') {
            return;
        }

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (this.selectedIndex < Math.min(this.filteredFiles.length - 1, 49)) {
                    this.selectedIndex++;
                    this.updateSelection();
                    this.scrollToSelected();
                }
                break;

            case 'ArrowUp':
                e.preventDefault();
                if (this.selectedIndex > 0) {
                    this.selectedIndex--;
                    this.updateSelection();
                    this.scrollToSelected();
                }
                break;

            case 'ArrowRight':
                e.preventDefault();
                this.showPreview();
                break;

            case 'ArrowLeft':
                e.preventDefault();
                if (this.previewVisible) {
                    this.hidePreview();
                }
                break;

            case 'Enter':
                e.preventDefault();
                this.confirmSelection();
                break;

            case 'Escape':
                e.preventDefault();
                if (this.previewVisible) {
                    this.hidePreview();
                } else {
                    this.close();
                }
                break;
        }
    }

    private scrollToSelected(): void {
        const items = this.notesContainer?.querySelectorAll('.stella-note-item');
        items?.[this.selectedIndex]?.scrollIntoView({ block: 'nearest' });
    }
}
