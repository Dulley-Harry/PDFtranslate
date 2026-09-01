import {
  App,
  FileSystemAdapter,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
  TFile,
  normalizePath,
} from 'obsidian';
import { execFile } from 'node:child_process';
import * as path from 'node:path';


type OutputMode = 'dual' | 'mono' | 'both';

interface PDFtranslateSettings {
  executablePath: string;
  outputFolder: string;
  mode: OutputMode;
  openAfterTranslation: boolean;
}

interface TranslationResult {
  input_pdf: string;
  mono_pdf: string | null;
  dual_pdf: string | null;
}

const DEFAULT_SETTINGS: PDFtranslateSettings = {
  executablePath: process.env.PDFTRANSLATE_PDF_EXECUTABLE || 'pdftranslate-pdf',
  outputFolder: 'PDFtranslate',
  mode: 'dual',
  openAfterTranslation: false,
};

const MAX_PROCESS_OUTPUT = 4 * 1024 * 1024;
const MAX_DIAGNOSTIC_TEXT = 1200;

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function diagnosticTail(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return '<empty>';
  const tail = trimmed.slice(-MAX_DIAGNOSTIC_TEXT);
  const prefix = trimmed.length > tail.length ? '…' : '';
  return JSON.stringify(`${prefix}${tail}`);
}

function streamDiagnostic(label: string, value: string): string {
  const bytes = new TextEncoder().encode(value).length;
  return `${label} (${bytes} bytes): ${diagnosticTail(value)}`;
}

function translationResultContractError(value: unknown): string | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return 'result must be an object';
  }

  const result = value as Record<string, unknown>;
  if (typeof result.input_pdf !== 'string' || result.input_pdf.length === 0) {
    return 'input_pdf must be a non-empty string';
  }
  for (const field of ['mono_pdf', 'dual_pdf'] as const) {
    const output = result[field];
    if (output !== null && (typeof output !== 'string' || output.length === 0)) {
      return `${field} must be a non-empty string or null`;
    }
  }
  if (result.mono_pdf === null && result.dual_pdf === null) {
    return 'mono_pdf and dual_pdf cannot both be null';
  }
  return null;
}

function parseTranslationResult(stdout: string, stderr: string): TranslationResult {
  const normalized = stdout.replace(/^\uFEFF/, '').trim();
  let parsed: unknown;
  try {
    parsed = JSON.parse(normalized) as unknown;
  } catch (strictError) {
    const lines = normalized
      .split(/\r?\n|\r/)
      .map((line) => line.replace(/^\uFEFF/, '').trim())
      .filter((line) => line.startsWith('{') && line.endsWith('}'));

    for (let index = lines.length - 1; index >= 0; index -= 1) {
      try {
        const candidate = JSON.parse(lines[index]) as unknown;
        if (translationResultContractError(candidate) === null) {
          console.warn(
            '[PDFtranslate] Recovered final JSON object from noisy stdout.',
            streamDiagnostic('stdout', stdout),
            streamDiagnostic('stderr', stderr),
          );
          return candidate as TranslationResult;
        }
      } catch {
        // Keep looking for the final complete JSON-line contract.
      }
    }

    throw new Error(
      [
        `PDFtranslate JSON parse failed: ${errorMessage(strictError)}`,
        streamDiagnostic('stdout', stdout),
        streamDiagnostic('stderr', stderr),
      ].join('\n'),
    );
  }

  const contractError = translationResultContractError(parsed);
  if (contractError !== null) {
    throw new Error(
      [
        `PDFtranslate JSON contract violation: ${contractError}`,
        streamDiagnostic('stdout', stdout),
        streamDiagnostic('stderr', stderr),
      ].join('\n'),
    );
  }
  return parsed as TranslationResult;
}

function runExecutable(
  command: string,
  args: string[],
): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    execFile(
      command,
      args,
      {
        windowsHide: true,
        maxBuffer: MAX_PROCESS_OUTPUT,
        env: process.env,
        encoding: 'utf8',
      },
      (error, stdout, stderr) => {
        const stdoutText = String(stdout ?? '');
        const stderrText = String(stderr ?? '');
        if (error) {
          const detail = (stderrText || stdoutText || error.message).trim();
          reject(new Error(detail.slice(-3000)));
          return;
        }
        resolve({ stdout: stdoutText, stderr: stderrText });
      },
    );
  });
}

function isInside(basePath: string, candidatePath: string): boolean {
  const relative = path.relative(basePath, candidatePath);
  return (
    relative === '' ||
    (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
  );
}

export default class PDFtranslatePlugin extends Plugin {
  override settings: PDFtranslateSettings = DEFAULT_SETTINGS;
  private busy = false;

  override async onload(): Promise<void> {
    await this.loadSettings();

    this.addCommand({
      id: 'translate-active-pdf',
      name: 'Translate active PDF with PDFtranslate',
      checkCallback: (checking: boolean) => {
        const file = this.app.workspace.getActiveFile();
        const available = Boolean(file && file.extension.toLowerCase() === 'pdf' && !this.busy);
        if (available && !checking && file) void this.translateFile(file);
        return available;
      },
    });

    this.addRibbonIcon('languages', 'Translate active PDF with PDFtranslate', () => {
      const file = this.app.workspace.getActiveFile();
      if (!file || file.extension.toLowerCase() !== 'pdf') {
        new Notice('Open a PDF first.');
        return;
      }
      void this.translateFile(file);
    });

    this.registerEvent(
      this.app.workspace.on('file-menu', (menu, file) => {
        if (!(file instanceof TFile) || file.extension.toLowerCase() !== 'pdf') return;
        menu.addItem((item) => {
          item
            .setTitle('Translate PDF with PDFtranslate')
            .setIcon('languages')
            .onClick(() => void this.translateFile(file));
        });
      }),
    );

    this.addSettingTab(new PDFtranslateSettingTab(this.app, this));
  }

  async loadSettings(): Promise<void> {
    const saved = (await this.loadData()) as Partial<PDFtranslateSettings> | null;
    this.settings = Object.assign({}, DEFAULT_SETTINGS, saved ?? {});
    if (!['dual', 'mono', 'both'].includes(this.settings.mode)) this.settings.mode = 'dual';
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }

  private getFileSystemAdapter(): FileSystemAdapter {
    const adapter = this.app.vault.adapter;
    if (!(adapter instanceof FileSystemAdapter)) {
      throw new Error('PDFtranslate requires a desktop file-system vault.');
    }
    return adapter;
  }

  private resolveOutputDirectory(vaultBasePath: string): string {
    const configured = this.settings.outputFolder.trim() || 'PDFtranslate';
    if (path.isAbsolute(configured)) {
      throw new Error('Output folder must be relative to the current Obsidian vault.');
    }
    const output = path.resolve(vaultBasePath, configured);
    if (!isInside(vaultBasePath, output)) {
      throw new Error('Output folder cannot leave the current Obsidian vault.');
    }
    return output;
  }

  private absoluteToVaultPath(vaultBasePath: string, absolutePath: string): string | null {
    const resolved = path.resolve(absolutePath);
    if (!isInside(vaultBasePath, resolved)) return null;
    const relative = path.relative(vaultBasePath, resolved).split(path.sep).join('/');
    return normalizePath(relative);
  }

  private async waitForVaultFile(vaultPath: string): Promise<TFile | null> {
    for (let attempt = 0; attempt < 12; attempt += 1) {
      const file = this.app.vault.getAbstractFileByPath(vaultPath);
      if (file instanceof TFile) return file;
      await new Promise((resolve) => window.setTimeout(resolve, 250));
    }
    return null;
  }

  async translateFile(file: TFile): Promise<void> {
    if (this.busy) {
      new Notice('A PDFtranslate job is already running.');
      return;
    }
    if (file.extension.toLowerCase() !== 'pdf') {
      new Notice('PDFtranslate only accepts PDF files.');
      return;
    }

    this.busy = true;
    const startNotice = new Notice(`PDFtranslate: translating ${file.name}…`, 0);
    try {
      const adapter = this.getFileSystemAdapter();
      const vaultBasePath = path.resolve(adapter.getBasePath());
      const inputPath = path.resolve(vaultBasePath, file.path);
      if (!isInside(vaultBasePath, inputPath)) {
        throw new Error('Active PDF resolves outside the current vault.');
      }
      const outputDirectory = this.resolveOutputDirectory(vaultBasePath);
      const executable = this.settings.executablePath.trim() || 'pdftranslate-pdf';
      const args = [
        inputPath,
        '--mode',
        this.settings.mode,
        '--output-dir',
        outputDirectory,
        '--json',
      ];

      const { stdout, stderr } = await runExecutable(executable, args);
      const result = parseTranslationResult(stdout, stderr);

      const outputs = [result.dual_pdf, result.mono_pdf].filter(
        (value): value is string => typeof value === 'string' && value.length > 0,
      );
      if (!outputs.length) throw new Error('PDFtranslate did not return a translated PDF.');

      const vaultOutputs = outputs
        .map((output) => this.absoluteToVaultPath(vaultBasePath, output))
        .filter((value): value is string => value !== null);
      if (!vaultOutputs.length) {
        throw new Error('Translated PDF was created outside the configured vault output folder.');
      }

      startNotice.hide();
      new Notice(
        `PDFtranslate complete:\n${vaultOutputs.join('\n')}`,
        10000,
      );

      if (this.settings.openAfterTranslation) {
        const translated = await this.waitForVaultFile(vaultOutputs[0]);
        if (translated) await this.app.workspace.getLeaf(false).openFile(translated);
      }
    } catch (error) {
      startNotice.hide();
      const message = error instanceof Error ? error.message : String(error);
      new Notice(`PDFtranslate failed: ${message}`, 15000);
      console.error('[PDFtranslate]', error);
    } finally {
      this.busy = false;
    }
  }
}

class PDFtranslateSettingTab extends PluginSettingTab {
  constructor(app: App, private readonly plugin: PDFtranslatePlugin) {
    super(app, plugin);
  }

  override display(): void {
    const { containerEl } = this;
    containerEl.empty();

    new Setting(containerEl)
      .setName('PDFtranslate executable')
      .setDesc('Local pdftranslate-pdf command or absolute executable path. No API credential is stored here.')
      .addText((text) =>
        text
          .setPlaceholder('pdftranslate-pdf')
          .setValue(this.plugin.settings.executablePath)
          .onChange(async (value) => {
            this.plugin.settings.executablePath = value.trim() || 'pdftranslate-pdf';
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName('Output folder')
      .setDesc('Folder inside this vault. Absolute paths and ../ traversal are rejected.')
      .addText((text) =>
        text
          .setPlaceholder('PDFtranslate')
          .setValue(this.plugin.settings.outputFolder)
          .onChange(async (value) => {
            this.plugin.settings.outputFolder = value.trim() || 'PDFtranslate';
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName('Output mode')
      .setDesc('Bilingual PDF, Chinese-only PDF, or both.')
      .addDropdown((dropdown) =>
        dropdown
          .addOption('dual', 'Bilingual')
          .addOption('mono', 'Chinese only')
          .addOption('both', 'Both')
          .setValue(this.plugin.settings.mode)
          .onChange(async (value) => {
            this.plugin.settings.mode = value as OutputMode;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName('Open translated PDF')
      .setDesc('Open the first generated PDF after Obsidian detects it in the vault.')
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.openAfterTranslation)
          .onChange(async (value) => {
            this.plugin.settings.openAfterTranslation = value;
            await this.plugin.saveSettings();
          }),
      );
  }
}
