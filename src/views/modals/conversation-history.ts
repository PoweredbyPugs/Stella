import { App } from 'obsidian';
import { StellaModal, ConversationSelectCallbacks } from './base';
import { Conversation } from '../../types';

interface ConversationHistoryConfig {
    conversations: Conversation[];
    currentConversationId: string | null;
}

// Conversation history modal with pagination and preview
export class ConversationHistoryModal extends StellaModal {
    private conversations: Conversation[];
    private currentConversationId: string | null;
    private callbacks: ConversationSelectCallbacks;

    private readonly ITEMS_PER_PAGE = 20;
    private currentPage = 0;
    private selectedIndex = 0;
    private previewVisible = false;

    private leftPanel: HTMLElement | null = null;
    private rightPanel: HTMLElement | null = null;
    private previewContent: HTMLElement | null = null;
    private conversationsContainer: HTMLElement | null = null;
    private headerContainer: HTMLElement | null = null;

    constructor(app: App, config: ConversationHistoryConfig, callbacks: ConversationSelectCallbacks) {
        super(app, { title: 'Conversations' });
        this.conversations = config.conversations;
        this.currentConversationId = config.currentConversationId;
        this.callbacks = callbacks;
    }

    protected buildContent(): void {
        if (this.conversations.length === 0) {
            this.contentEl.createEl('p', {
                text: 'No conversations yet. Start chatting to create your first conversation.'
            });
            return;
        }

        const { leftPanel, rightPanel, previewContent } = this.createTwoPanelLayout();
        this.leftPanel = leftPanel;
        this.rightPanel = rightPanel;
        this.previewContent = previewContent;
        previewContent.textContent = 'Select a conversation and press → to preview';

        const totalPages = Math.ceil(this.conversations.length / this.ITEMS_PER_PAGE);

        // Create pagination header if needed
        this.headerContainer = leftPanel.createDiv({ cls: 'stella-pagination-header' });
        if (totalPages > 1) {
            this.renderPaginationHeader();
        }

        // Conversations container
        this.conversationsContainer = leftPanel.createDiv({ cls: 'stella-conversations-container' });

        // Initial render
        this.renderConversationPage();

        // Initially hide preview
        this.hidePreview();

        // Setup keyboard navigation
        this.modalEl.addEventListener('keydown', (e) => this.handleKeydown(e));
    }

    private renderPaginationHeader(): void {
        if (!this.headerContainer) return;

        this.headerContainer.empty();
        const totalPages = Math.ceil(this.conversations.length / this.ITEMS_PER_PAGE);

        this.headerContainer.createDiv({
            cls: 'stella-page-info',
            text: `Page ${this.currentPage + 1} of ${totalPages} (${this.conversations.length} conversations)`
        });

        const paginationControls = this.headerContainer.createDiv({ cls: 'stella-pagination-controls' });

        const prevBtn = paginationControls.createEl('button', {
            cls: 'stella-pagination-btn',
            text: '← Prev'
        });
        prevBtn.disabled = this.currentPage === 0;
        prevBtn.addEventListener('click', () => this.prevPage());

        const nextBtn = paginationControls.createEl('button', {
            cls: 'stella-pagination-btn',
            text: 'Next →'
        });
        nextBtn.disabled = this.currentPage === totalPages - 1;
        nextBtn.addEventListener('click', () => this.nextPage());
    }

    private renderConversationPage(): void {
        if (!this.conversationsContainer) return;

        this.conversationsContainer.empty();

        const startIndex = this.currentPage * this.ITEMS_PER_PAGE;
        const endIndex = Math.min(startIndex + this.ITEMS_PER_PAGE, this.conversations.length);
        const pageConversations = this.conversations.slice(startIndex, endIndex);

        pageConversations.forEach((conversation, relativeIndex) => {
            const convEl = this.conversationsContainer!.createDiv({ cls: 'stella-conversation-item' });

            if (conversation.id === this.currentConversationId) {
                convEl.classList.add('stella-conversation-current');
            }

            if (relativeIndex === this.selectedIndex) {
                convEl.classList.add('selected');
            }

            const titleEl = convEl.createDiv({ cls: 'stella-conversation-title' });
            titleEl.textContent = conversation.title;

            const metaEl = convEl.createDiv({ cls: 'stella-conversation-meta' });
            const messageCount = conversation.messages.length;
            const lastUpdate = new Date(conversation.updatedAt).toLocaleDateString();
            metaEl.textContent = `${messageCount} messages • Last updated ${lastUpdate}`;

            // Delete button
            const deleteBtn = convEl.createEl('div', {
                cls: 'stella-conversation-delete',
                attr: { title: 'Delete conversation' }
            });
            deleteBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3,6 5,6 21,6"></polyline><path d="M8,6V4c0-1,1-2,2-2h4c1,0,2-1,2-2v2M10,11v6M14,11v6"></path><path d="M5,6l1,14c0,1,1,2,2,2h8c1,0,2-1,2-2l1-14"></path></svg>';

            deleteBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                await this.callbacks.onDelete(conversation.id);
                // Refresh the list
                this.conversations = this.conversations.filter(c => c.id !== conversation.id);
                if (this.selectedIndex >= pageConversations.length - 1) {
                    this.selectedIndex = Math.max(0, this.selectedIndex - 1);
                }
                this.renderConversationPage();
                this.renderPaginationHeader();
            });

            // Click to load
            convEl.addEventListener('click', (e) => {
                if (!(e.target as Element).closest('.stella-conversation-delete')) {
                    this.callbacks.onSelect(conversation.id);
                    this.close();
                }
            });
        });

        this.fixConversationsHeight();
    }

    private prevPage(): void {
        if (this.currentPage > 0) {
            this.currentPage--;
            this.selectedIndex = 0;
            this.renderConversationPage();
            this.renderPaginationHeader();
        }
    }

    private nextPage(): void {
        const totalPages = Math.ceil(this.conversations.length / this.ITEMS_PER_PAGE);
        if (this.currentPage < totalPages - 1) {
            this.currentPage++;
            this.selectedIndex = 0;
            this.renderConversationPage();
            this.renderPaginationHeader();
        }
    }

    private showPreview(): void {
        const startIndex = this.currentPage * this.ITEMS_PER_PAGE;
        const conversation = this.conversations[startIndex + this.selectedIndex];
        if (!conversation || !this.previewContent || !this.leftPanel || !this.rightPanel) return;

        this.previewContent.empty();

        // Create conversation summary
        const summaryDiv = this.previewContent.createDiv({ cls: 'stella-conversation-summary' });

        const infoDiv = summaryDiv.createDiv({ cls: 'stella-conversation-info' });
        infoDiv.innerHTML = `
            <div><strong>Messages:</strong> ${conversation.messages.length}</div>
            <div><strong>Created:</strong> ${new Date(conversation.createdAt).toLocaleString()}</div>
            <div><strong>Updated:</strong> ${new Date(conversation.updatedAt).toLocaleString()}</div>
        `;

        if (conversation.systemPrompt) {
            const sysPromptDiv = summaryDiv.createDiv({ cls: 'stella-system-prompt-preview' });
            sysPromptDiv.createEl('h4', { text: 'System Prompt:' });
            const promptContent = sysPromptDiv.createDiv({ cls: 'stella-prompt-content' });
            promptContent.textContent = conversation.systemPrompt.substring(0, 200) +
                (conversation.systemPrompt.length > 200 ? '...' : '');
        }

        // Messages preview
        if (conversation.messages.length > 0) {
            const messagesDiv = summaryDiv.createDiv({ cls: 'stella-messages-preview' });
            messagesDiv.createEl('h4', { text: 'Messages Preview:' });

            conversation.messages.slice(0, 4).forEach((msg) => {
                const msgDiv = messagesDiv.createDiv({
                    cls: `stella-preview-message stella-preview-${msg.role}`
                });
                const roleSpan = msgDiv.createEl('span', { cls: 'stella-preview-role' });
                roleSpan.textContent = msg.role === 'user' ? '👤' : '🤖';

                const contentDiv = msgDiv.createDiv({ cls: 'stella-preview-content' });
                contentDiv.textContent = msg.content.length > 150
                    ? msg.content.substring(0, 150) + '...'
                    : msg.content;
            });

            if (conversation.messages.length > 4) {
                const moreDiv = messagesDiv.createDiv({ cls: 'stella-preview-more' });
                moreDiv.textContent = `... and ${conversation.messages.length - 4} more messages`;
            }
        }

        this.rightPanel.style.display = 'block';
        this.previewVisible = true;

        this.modalEl.style.width = '60vw';
        this.modalEl.style.maxWidth = '980px';
        this.leftPanel.style.width = '50%';
        this.rightPanel.style.width = '50%';

        this.fixConversationsHeight();
    }

    private hidePreview(): void {
        if (!this.leftPanel || !this.rightPanel) return;

        this.rightPanel.style.display = 'none';
        this.leftPanel.style.width = '100%';
        this.previewVisible = false;

        this.modalEl.style.width = '400px';
        this.modalEl.style.maxWidth = 'none';

        this.fixConversationsHeight();
    }

    private fixConversationsHeight(): void {
        if (!this.conversationsContainer || !this.headerContainer) return;

        setTimeout(() => {
            const modalHeight = this.modalEl.clientHeight;
            const titleHeight = this.titleEl.offsetHeight;
            const headerHeight = this.headerContainer?.offsetHeight || 0;
            const padding = 40;

            const availableHeight = modalHeight - titleHeight - headerHeight - padding;
            this.conversationsContainer!.style.height = `${availableHeight}px`;
            this.conversationsContainer!.style.maxHeight = `${availableHeight}px`;
            this.conversationsContainer!.style.overflow = 'auto';
        }, 50);
    }

    private updateSelection(): void {
        const items = this.conversationsContainer?.querySelectorAll('.stella-conversation-item');
        items?.forEach((item, i) => {
            item.classList.toggle('selected', i === this.selectedIndex);
        });
    }

    private handleKeydown(e: KeyboardEvent): void {
        const startIndex = this.currentPage * this.ITEMS_PER_PAGE;
        const pageSize = Math.min(this.ITEMS_PER_PAGE, this.conversations.length - startIndex);

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (this.selectedIndex < pageSize - 1) {
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
                const conversation = this.conversations[startIndex + this.selectedIndex];
                if (conversation) {
                    this.callbacks.onSelect(conversation.id);
                    this.close();
                }
                break;

            case 'Escape':
                e.preventDefault();
                if (this.previewVisible) {
                    this.hidePreview();
                } else {
                    this.close();
                }
                break;

            case 'PageDown':
                e.preventDefault();
                this.nextPage();
                break;

            case 'PageUp':
                e.preventDefault();
                this.prevPage();
                break;
        }
    }

    private scrollToSelected(): void {
        const items = this.conversationsContainer?.querySelectorAll('.stella-conversation-item');
        items?.[this.selectedIndex]?.scrollIntoView({ block: 'nearest' });
    }
}
