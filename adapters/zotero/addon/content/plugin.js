(function (root) {
  "use strict";

  const PREF_PREFIX = "extensions.pdftranslate.";
  const TRANSLATED_PREFIXES = [
    "[PDFtranslate 双语]",
    "[PDFtranslate 中文]",
    "[PDFtranslate]",
  ];

  class PDFtranslateZoteroPlugin {
    constructor({ id, version, rootURI }) {
      this.id = id;
      this.version = version;
      this.rootURI = rootURI;
      this.menuRegistrationID = null;
      this.busy = false;
      this.activeProcess = null;
      this._subprocessModule = null;
    }

    async startup() {
      await Zotero.initializationPromise;
      this.registerMenu();
      for (const window of Zotero.getMainWindows()) this.onMainWindowLoad(window);
      Zotero.debug(`[PDFtranslate] Zotero adapter ${this.version} started`);
    }

    async shutdown() {
      if (this.activeProcess) {
        try {
          this.activeProcess.kill();
        } catch (_error) {}
      }
      this.activeProcess = null;
      if (this.menuRegistrationID && Zotero.MenuManager?.unregisterMenu) {
        Zotero.MenuManager.unregisterMenu(this.menuRegistrationID);
      }
      this.menuRegistrationID = null;
      for (const window of Zotero.getMainWindows()) this.onMainWindowUnload(window);
    }

    onMainWindowLoad(window) {
      try {
        window.MozXULElement?.insertFTLIfNeeded("pdftranslate.ftl");
      } catch (error) {
        Zotero.logError(error);
      }
    }

    onMainWindowUnload(window) {
      window.document?.querySelector('link[href="pdftranslate.ftl"]')?.remove();
    }

    registerMenu() {
      this.menuRegistrationID = Zotero.MenuManager.registerMenu({
        menuID: "pdftranslate-item-menu",
        pluginID: this.id,
        target: "main/library/item",
        menus: [
          {
            menuType: "menuitem",
            l10nID: "pdftranslate-menu-translate",
            onShowing: (_event, context) => {
              const items = context.items || [];
              context.setVisible(items.some((item) => this.isPotentialSource(item)));
              context.setEnabled(!this.busy);
            },
            onCommand: (_event, context) => {
              void this.translateItems(context.items || []).catch((error) => {
                Zotero.logError(error);
                this.alert(error.message || String(error));
              });
            },
          },
        ],
      });
    }

    isPotentialSource(item) {
      if (!item) return false;
      if (item.isRegularItem?.()) return true;
      if (!item.isPDFAttachment?.()) return false;
      const title = String(item.getField?.("title") || "");
      return !TRANSLATED_PREFIXES.some((prefix) => title.startsWith(prefix));
    }

    getConfig() {
      const read = (name, fallback) => {
        const value = Zotero.Prefs.get(PREF_PREFIX + name, true);
        return value === undefined || value === null ? fallback : value;
      };

      let executable = String(read("executablePath", "pdftranslate-pdf")).trim();
      try {
        const envValue = Services.env.get("PDFTRANSLATE_PDF_EXECUTABLE");
        if (envValue) executable = envValue.trim();
      } catch (_error) {}

      let mode = String(read("mode", "dual")).trim().toLowerCase();
      try {
        const envValue = Services.env.get("PDFTRANSLATE_OUTPUT_MODE");
        if (envValue) mode = envValue.trim().toLowerCase();
      } catch (_error) {}
      if (!["dual", "mono", "both"].includes(mode)) mode = "dual";

      return {
        executable,
        mode,
        openAfterTranslation: Boolean(read("openAfterTranslation", false)),
      };
    }

    async translateItems(selectedItems) {
      if (this.busy) {
        this.alert(
          this.text(
            "已有 PDFtranslate 任务正在运行。",
            "A PDFtranslate job is already running.",
          ),
        );
        return;
      }

      const config = this.getConfig();
      const targets = await this.collectTargets(selectedItems);
      if (!targets.length) {
        this.alert(
          this.text(
            "没有找到可翻译的本地 PDF。",
            "No local PDF was found to translate.",
          ),
        );
        return;
      }

      this.busy = true;
      const progress = new Zotero.ProgressWindow({ closeOnClick: false });
      progress.changeHeadline("PDFtranslate");
      const itemProgress = new progress.ItemProgress(
        this.rootURI + "content/icon.svg",
        this.text("准备翻译……", "Preparing translation…"),
      );
      itemProgress.setProgress(0);
      progress.show();

      let completed = 0;
      const failures = [];
      try {
        for (let index = 0; index < targets.length; index += 1) {
          const target = targets[index];
          itemProgress.setText(
            this.text(
              `正在翻译 ${index + 1}/${targets.length}：${target.displayTitle}`,
              `Translating ${index + 1}/${targets.length}: ${target.displayTitle}`,
            ),
          );
          try {
            const imported = await this.translateOne(target, config);
            completed += imported.length;
            if (
              config.openAfterTranslation &&
              targets.length === 1 &&
              imported.length
            ) {
              await Zotero.getActiveZoteroPane()?.viewAttachment(imported[0].id);
            }
          } catch (error) {
            Zotero.logError(error);
            failures.push(`${target.displayTitle}: ${error.message || String(error)}`);
          }
          itemProgress.setProgress(Math.round(((index + 1) / targets.length) * 100));
        }

        if (failures.length) {
          itemProgress.setError();
          itemProgress.setText(
            this.text(
              `完成 ${completed} 个附件，失败 ${failures.length} 篇`,
              `${completed} attachment(s) created; ${failures.length} item(s) failed`,
            ),
          );
          for (const failure of failures.slice(0, 5)) progress.addDescription(failure);
          progress.startCloseTimer(12000, true);
        } else {
          itemProgress.setProgress(100);
          itemProgress.setText(
            this.text(
              `翻译完成，共生成 ${completed} 个附件`,
              `Translation complete: ${completed} attachment(s)`,
            ),
          );
          progress.startCloseTimer(5000, true);
        }
      } finally {
        this.busy = false;
      }
    }

    async collectTargets(items) {
      const targets = [];
      const seen = new Set();
      for (const item of items || []) {
        let attachment = null;
        if (item?.isPDFAttachment?.()) {
          attachment = item;
        } else if (item?.isRegularItem?.()) {
          attachment = await this.findBestPDFAttachment(item);
        }
        if (!attachment || seen.has(attachment.id)) continue;
        seen.add(attachment.id);

        const title = String(attachment.getField?.("title") || "");
        if (TRANSLATED_PREFIXES.some((prefix) => title.startsWith(prefix))) continue;

        const path = await attachment.getFilePathAsync();
        if (!path || !(await this.ioUtils().exists(path))) continue;

        const parent = attachment.parentID
          ? await Zotero.Items.getAsync(attachment.parentID)
          : null;
        const library = Zotero.Libraries.get(attachment.libraryID);
        if (library?.filesEditable === false) continue;

        targets.push({
          attachment,
          parent,
          path,
          displayTitle:
            parent?.getField("title") ||
            attachment.getField("title") ||
            attachment.attachmentFilename ||
            "PDF",
        });
      }
      return targets;
    }

    async findBestPDFAttachment(item) {
      try {
        const best = await item.getBestAttachment();
        if (best?.isPDFAttachment?.() && (await best.fileExists())) return best;
      } catch (error) {
        Zotero.debug(`[PDFtranslate] getBestAttachment failed: ${error.message}`);
      }
      const children = await Zotero.Items.getAsync(item.getAttachments());
      for (const child of children) {
        if (child?.isPDFAttachment?.() && (await child.fileExists())) return child;
      }
      return null;
    }

    async translateOne(target, config) {
      const ioUtils = this.ioUtils();
      const pathUtils = this.pathUtils();
      const jobID = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
      const jobDirectory = pathUtils.join(
        Zotero.getTempDirectory().path,
        "pdftranslate-zotero",
        jobID,
      );
      await ioUtils.makeDirectory(jobDirectory, { ignoreExisting: true });

      try {
        const command = await this.resolveCommand(config.executable);
        const args = [
          target.path,
          "--mode",
          config.mode,
          "--output-dir",
          jobDirectory,
          "--json",
        ];
        const { stdout, stderr, exitCode } = await this.runProcess(command, args);
        if (exitCode !== 0) {
          const detail = this.tail(stderr || stdout, 2500);
          throw new Error(
            detail ||
              this.text(
                `PDFtranslate 退出码 ${exitCode}`,
                `PDFtranslate exited with code ${exitCode}`,
              ),
          );
        }

        let result;
        try {
          result = JSON.parse(stdout.trim());
        } catch (_error) {
          throw new Error(
            this.text(
              "PDFtranslate 返回的结果不是有效 JSON。",
              "PDFtranslate returned invalid JSON.",
            ),
          );
        }

        const outputs = [];
        if ((config.mode === "dual" || config.mode === "both") && result.dual_pdf) {
          outputs.push({ path: result.dual_pdf, kind: "dual" });
        }
        if ((config.mode === "mono" || config.mode === "both") && result.mono_pdf) {
          outputs.push({ path: result.mono_pdf, kind: "mono" });
        }
        if (!outputs.length) {
          throw new Error(
            this.text("没有生成可导入的 PDF。", "No translated PDF was produced."),
          );
        }

        const imported = [];
        for (const output of outputs) {
          if (!(await ioUtils.exists(output.path))) {
            throw new Error(
              this.text(
                "翻译结果文件不存在。",
                "Translated output file does not exist.",
              ),
            );
          }
          const title =
            output.kind === "dual"
              ? `[PDFtranslate 双语] ${target.displayTitle}`
              : `[PDFtranslate 中文] ${target.displayTitle}`;
          imported.push(
            await Zotero.Attachments.importFromFile({
              file: output.path,
              parentItemID: target.parent?.id,
              libraryID: target.parent ? undefined : target.attachment.libraryID,
              title,
              contentType: "application/pdf",
              moveFile: true,
            }),
          );
        }
        return imported;
      } finally {
        try {
          await ioUtils.remove(jobDirectory, { recursive: true, ignoreAbsent: true });
        } catch (error) {
          Zotero.debug(`[PDFtranslate] temporary cleanup failed: ${error.message}`);
        }
      }
    }

    async runProcess(command, args) {
      const Subprocess = this.subprocess();
      const process = await Subprocess.call({
        command,
        arguments: args,
        stdout: "pipe",
        stderr: "pipe",
      });
      this.activeProcess = process;
      const stdoutPromise = this.readStream(process.stdout, 2 * 1024 * 1024);
      const stderrPromise = this.readStream(process.stderr, 128 * 1024);
      let waitResult;
      try {
        waitResult = await process.wait();
      } finally {
        this.activeProcess = null;
      }
      const [stdout, stderr] = await Promise.all([stdoutPromise, stderrPromise]);
      return { stdout, stderr, exitCode: this.exitCode(waitResult) };
    }

    async readStream(stream, maxLength) {
      if (!stream?.readString) return "";
      let output = "";
      while (true) {
        let chunk;
        try {
          chunk = await stream.readString();
        } catch (_error) {
          break;
        }
        if (!chunk) break;
        output = (output + chunk).slice(-maxLength);
      }
      return output;
    }

    async resolveCommand(value) {
      const command = String(value || "").trim();
      if (!command) {
        throw new Error(
          this.text(
            "PDFtranslate 可执行文件路径为空。",
            "PDFtranslate executable is empty.",
          ),
        );
      }
      if (this.pathUtils().isAbsolute(command)) {
        if (await this.ioUtils().exists(command)) return command;
        throw new Error(
          this.text(`找不到 ${command}`, `Executable not found: ${command}`),
        );
      }
      try {
        return await this.subprocess().pathSearch(command);
      } catch (_error) {
        throw new Error(
          this.text(
            `找不到“${command}”。请把 pdftranslate-pdf 加入 PATH，或设置环境变量 PDFTRANSLATE_PDF_EXECUTABLE。`,
            `Could not find “${command}”. Put pdftranslate-pdf on PATH or set PDFTRANSLATE_PDF_EXECUTABLE.`,
          ),
        );
      }
    }

    subprocess() {
      if (!this._subprocessModule) {
        const module = ChromeUtils.importESModule(
          "resource://gre/modules/Subprocess.sys.mjs",
        );
        this._subprocessModule = module.Subprocess || module.default || module;
      }
      return this._subprocessModule;
    }

    pathUtils() {
      if (root.PathUtils) return root.PathUtils;
      return ChromeUtils.importESModule(
        "resource://gre/modules/PathUtils.sys.mjs",
      ).PathUtils;
    }

    ioUtils() {
      if (root.IOUtils) return root.IOUtils;
      return ChromeUtils.importESModule(
        "resource://gre/modules/IOUtils.sys.mjs",
      ).IOUtils;
    }

    exitCode(waitResult) {
      if (typeof waitResult === "number") return waitResult;
      if (typeof waitResult?.exitCode === "number") return waitResult.exitCode;
      return 0;
    }

    tail(value, length) {
      return String(value || "").trim().slice(-length);
    }

    text(zh, en) {
      return String(Zotero.locale || "").toLowerCase().startsWith("zh") ? zh : en;
    }

    alert(message) {
      Zotero.alert(null, "PDFtranslate", String(message));
    }
  }

  root.PDFtranslateZoteroPlugin = PDFtranslateZoteroPlugin;
})(typeof globalThis !== "undefined" ? globalThis : this);
