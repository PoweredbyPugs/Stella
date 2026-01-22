import { App, FuzzySuggestModal, TAbstractFile, TFile, TFolder } from 'obsidian';

/**
 * Modal for selecting folders from the vault using fuzzy search
 */
export class FolderSuggestModal extends FuzzySuggestModal<TFolder> {
    private folders: TFolder[];
    private onChoose: (folder: TFolder) => void;

    constructor(app: App, folders: TAbstractFile[], onChoose: (folder: TFolder) => void) {
        super(app);
        this.folders = folders.filter((f): f is TFolder => f instanceof TFolder);
        this.onChoose = onChoose;
        this.setPlaceholder("Type to search folders...");
    }

    getItems(): TFolder[] {
        return this.folders;
    }

    getItemText(item: TFolder): string {
        return item.path;
    }

    onChooseItem(item: TFolder, evt: MouseEvent | KeyboardEvent): void {
        this.onChoose(item);
    }
}

/**
 * Modal for selecting files from the vault using fuzzy search
 */
export class FileSuggestModal extends FuzzySuggestModal<TFile> {
    private files: TFile[];
    private onChoose: (file: TFile) => void;

    constructor(app: App, files: TFile[], onChoose: (file: TFile) => void) {
        super(app);
        this.files = files;
        this.onChoose = onChoose;
        this.setPlaceholder("Type to search files...");
    }

    getItems(): TFile[] {
        return this.files;
    }

    getItemText(item: TFile): string {
        return item.path;
    }

    onChooseItem(item: TFile, evt: MouseEvent | KeyboardEvent): void {
        this.onChoose(item);
    }
}
