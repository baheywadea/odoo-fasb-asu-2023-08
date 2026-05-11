/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

let inited = false;
let pollingStarted = false;
let walletConnectBound = false;
let walletConnectGuardBound = false;
let activeWalletConnectProvider = null;
let walletConnectAttempt = 0;

bindWalletConnectErrorGuard();

function initCryptoPaymentPage() {
    if (inited) {
        return;
    }
    inited = true;

    const wrap = document.getElementById("wrap");
    if (!wrap) {
        return;
    }

    const txId = parseInt(wrap.dataset.txId || "0", 10);
    const token = wrap.dataset.token || "";
    if (!txId || !token) {
        setWalletStatus("Missing payment session data.", "text-warning mt-2");
        return;
    }

    setupCopyButtons();
    startCryptoPolling(txId, token);
    setupWalletConnect(txId, token, wrap.dataset.walletconnectProjectId || "");
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCryptoPaymentPage);
} else {
    initCryptoPaymentPage();
}

function setWalletStatus(text, className = "text-muted mt-2") {
    const status = document.getElementById("wc_status");
    if (status) {
        status.className = className;
        status.textContent = text || "";
    }
}

function startCryptoPolling(txId, token) {
    if (pollingStarted) {
        return;
    }
    pollingStarted = true;

    const box = document.getElementById("crypto_status_box");
    const setStatus = (cls, text) => {
        if (!box) {
            return;
        }
        box.className = `alert ${cls} mb-0`;
        box.textContent = text;
    };

    const poll = async () => {
        try {
            const res = await rpc(`/crypto/status/${txId}`, { token });
            if (res && res.paid) {
                setStatus("alert-success", "Payment confirmed. Redirecting...");
                window.location.href = "/payment/status";
                return;
            }
            if (res?.tx_hash) {
                const message = res.message || "Transaction sent. Waiting for blockchain confirmation...";
                const cls = ["failed", "mismatch"].includes(res.confirmation_status) ? "alert-warning" : "alert-info";
                setStatus(cls, message);
            }
            if (!res?.tx_hash) {
                setStatus("alert-info", res?.message || "Waiting for payment confirmation...");
            }
        } catch (_error) {
            setStatus("alert-warning", "Unable to check payment right now...");
        }
        setTimeout(poll, 2500);
    };

    poll();
}

function setupCopyButtons() {
    for (const button of document.querySelectorAll("[data-copy]")) {
        if (button.dataset.copyBound === "1") {
            continue;
        }
        button.dataset.copyBound = "1";
        button.addEventListener("click", async () => {
            const value = button.dataset.copy || "";
            const oldText = button.textContent;
            try {
                await navigator.clipboard.writeText(value);
                button.textContent = "Copied";
                setTimeout(() => {
                    button.textContent = oldText;
                }, 1500);
            } catch (_error) {
                setWalletStatus("Could not copy address automatically. Please copy it manually.", "text-warning mt-2");
            }
        });
    }
}

async function loadEthereumProvider() {
    const existing = getEthereumProvider();
    if (existing?.init) {
        return existing;
    }

    const moduleUrls = [
        "https://esm.sh/@walletconnect/ethereum-provider@2.21.8",
        "https://cdn.jsdelivr.net/npm/@walletconnect/ethereum-provider@2.21.8/+esm",
    ];
    for (const url of moduleUrls) {
        try {
            const module = await import(url);
            const provider = module.EthereumProvider || module.default?.EthereumProvider || module.default;
            if (provider?.init) {
                return provider;
            }
        } catch (_error) {
            // Try the next CDN.
        }
    }
    return null;
}

function getEthereumProvider() {
    if (window.WalletConnectEthereumProvider?.init) {
        return window.WalletConnectEthereumProvider;
    }
    if (window.WalletConnectEthereumProvider?.default?.init) {
        return window.WalletConnectEthereumProvider.default;
    }
    if (window.EthereumProvider?.init) {
        return window.EthereumProvider;
    }
    return null;
}

async function getPaymentIntent(txId, token) {
    const intent = await rpc(`/crypto/intent/${txId}`, { token });
    if (!intent?.ok) {
        throw new Error(intent?.error || "payment_intent_error");
    }
    return {
        chainId: Number(intent.chainId),
        to: intent.to,
        valueHex: `0x${BigInt(String(intent.valueWei || "0")).toString(16)}`,
        rpcUrl: intent.rpcUrl || "",
    };
}

async function storeTransactionHash(txId, token, txHash, fromAddress) {
    try {
        await rpc(`/crypto/wc_tx/${txId}`, {
            token,
            tx_hash: txHash,
            from_address: fromAddress,
        });
    } catch (_error) {
        // Webhook/polling can still confirm the transaction.
    }
}

function setupWalletConnect(txId, token, projectId) {
    if (walletConnectBound) {
        return;
    }
    walletConnectBound = true;

    const btn = document.getElementById("wc_connect_btn");
    if (!btn) {
        return;
    }

    btn.addEventListener("click", async () => {
        walletConnectAttempt += 1;
        const attempt = walletConnectAttempt;
        const oldText = btn.textContent;
        btn.dataset.defaultText = oldText;
        btn.disabled = true;
        let provider = null;

        try {
            if (!projectId) {
                throw new Error("missing_walletconnect_project_id");
            }

            btn.textContent = "Opening WalletConnect...";
            setWalletStatus("Preparing WalletConnect session...");
            await withTimeout(
                cleanupActiveWalletConnectProvider(),
                1500,
                "walletconnect_cleanup_timeout"
            ).catch(() => {});
            await withTimeout(
                clearWalletConnectStorage(),
                1500,
                "walletconnect_storage_cleanup_timeout"
            ).catch(() => {});

            const [EthereumProvider, intent] = await Promise.all([
                loadEthereumProvider(),
                getPaymentIntent(txId, token),
            ]);
            if (!EthereumProvider?.init) {
                throw new Error("walletconnect_provider_not_loaded");
            }

            provider = await EthereumProvider.init({
                projectId,
                chains: [intent.chainId],
                customStoragePrefix: `odoo_crypto_checkout_${txId}_${attempt}_${Date.now()}`,
                showQrModal: true,
                methods: ["eth_sendTransaction"],
                events: ["accountsChanged", "chainChanged", "disconnect"],
                rpcMap: buildRpcMap(intent),
                metadata: {
                    name: "Odoo Crypto Payment",
                    description: "Odoo crypto payment checkout",
                    url: window.location.origin,
                    icons: [`${window.location.origin}/web/image/website/1/favicon`],
                },
            });
            activeWalletConnectProvider = provider;
            bindProviderResetEvents(provider);

            await withTimeout(
                safeWalletConnectRequest(provider.connect({
                    chains: [intent.chainId],
                    rpcMap: buildRpcMap(intent),
                })),
                20000,
                "walletconnect_connection_timeout"
            );
            const accounts = provider.accounts?.length
                ? provider.accounts
                : walletConnectSessionAccounts(provider, intent.chainId);
            const from = accounts?.[0];
            if (!from) {
                throw new Error("walletconnect_no_account");
            }

            btn.textContent = "Approve payment in wallet...";
            setWalletStatus(`Connected: ${from}`);

            const txHash = await withTimeout(
                safeWalletConnectRequest(provider.request({
                    method: "eth_sendTransaction",
                    params: [{
                        from,
                        to: intent.to,
                        value: intent.valueHex,
                        data: "0x",
                    }],
                })),
                120000,
                "walletconnect_payment_timeout"
            );
            await storeTransactionHash(txId, token, txHash, from);

            setWalletStatus(`Transaction sent: ${txHash}`, "text-success mt-2");
            btn.textContent = "Transaction sent. Waiting confirmation...";
        } catch (error) {
            setWalletStatus(walletErrorMessage(error), "text-warning mt-2");
            await resetWalletConnectSession(provider);
        }
    });
}

function safeWalletConnectRequest(promise) {
    return Promise.resolve(promise).catch((error) => {
        throw normalizeWalletConnectError(error);
    });
}

function normalizeWalletConnectError(error) {
    const rawMessage = String(error?.message || error || "");
    if (walletErrorType(error) === "cancelled" || rawMessage.includes("User rejected methods")) {
        return new Error("walletconnect_cancelled");
    }
    return error;
}

function walletConnectSessionAccounts(provider, chainId) {
    const namespaces = provider?.session?.namespaces || {};
    const eip155Accounts = namespaces.eip155?.accounts || [];
    const prefix = `eip155:${chainId}:`;
    return eip155Accounts
        .filter((account) => String(account).startsWith(prefix))
        .map((account) => String(account).slice(prefix.length));
}

function withTimeout(promise, timeoutMs, errorMessage) {
    let timeoutId;
    const timeout = new Promise((_resolve, reject) => {
        timeoutId = setTimeout(() => reject(new Error(errorMessage)), timeoutMs);
    });
    return Promise.race([promise, timeout]).finally(() => clearTimeout(timeoutId));
}

function bindProviderResetEvents(provider) {
    if (!provider?.on || provider.__odooResetEventsBound) {
        return;
    }
    provider.__odooResetEventsBound = true;
    for (const eventName of ["disconnect", "session_delete", "session_expire"]) {
        provider.on(eventName, () => {
            setWalletStatus("WalletConnect was cancelled or disconnected. Please tap Pay with WalletConnect again.", "text-warning mt-2");
            resetWalletConnectButton();
        });
    }
}

async function cleanupActiveWalletConnectProvider(provider = activeWalletConnectProvider) {
    activeWalletConnectProvider = null;
    if (!provider) {
        return;
    }
    try {
        if (typeof provider.disconnect === "function") {
            await withTimeout(provider.disconnect(), 1000, "walletconnect_disconnect_timeout");
        }
    } catch (_error) {
        // Best-effort cleanup only.
    }
}

async function resetWalletConnectSession(provider = activeWalletConnectProvider) {
    await withTimeout(
        cleanupActiveWalletConnectProvider(provider),
        1500,
        "walletconnect_cleanup_timeout"
    ).catch(() => {});
    await withTimeout(
        clearWalletConnectStorage(),
        1500,
        "walletconnect_storage_cleanup_timeout"
    ).catch(() => {});
    resetWalletConnectButton();
}

function buildRpcMap(intent) {
    const rpcUrl = intent.rpcUrl || defaultRpcUrl(intent.chainId);
    return rpcUrl ? { [intent.chainId]: rpcUrl } : {};
}

function defaultRpcUrl(chainId) {
    const defaults = {
        1: "https://ethereum.publicnode.com",
        10: "https://mainnet.optimism.io",
        56: "https://bsc-dataseed.binance.org",
        137: "https://polygon-rpc.com",
        8453: "https://mainnet.base.org",
        42161: "https://arb1.arbitrum.io/rpc",
        43114: "https://api.avax.network/ext/bc/C/rpc",
        11155111: "https://ethereum-sepolia.publicnode.com",
    };
    return defaults[Number(chainId)] || "";
}

function bindWalletConnectErrorGuard() {
    if (walletConnectGuardBound) {
        return;
    }
    walletConnectGuardBound = true;

    const isHandledWalletConnectError = (reason) => walletErrorType(reason) !== "";
    const suppressWalletConnectError = (event, reason) => {
        if (!isHandledWalletConnectError(reason)) {
            return;
        }
        if (typeof event?.preventDefault === "function") {
            event.preventDefault();
        }
        if (typeof event?.stopImmediatePropagation === "function") {
            event.stopImmediatePropagation();
        }
        setWalletStatus(walletErrorMessage(reason), "text-warning mt-2");
        resetWalletConnectSession();
    };

    window.addEventListener("unhandledrejection", (event) => {
        suppressWalletConnectError(event, event?.reason);
    }, true);
    window.addEventListener("error", (event) => {
        suppressWalletConnectError(event, event?.error || event?.message);
    }, true);
}

function resetWalletConnectButton() {
    const btn = document.getElementById("wc_connect_btn");
    if (!btn) {
        return;
    }
    btn.disabled = false;
    btn.textContent = btn.dataset.defaultText || "Pay with WalletConnect";
}

async function clearWalletConnectStorage() {
    try {
        for (const storage of [window.localStorage, window.sessionStorage]) {
            for (const key of Object.keys(storage || {})) {
                if (isWalletConnectStorageKey(key)) {
                    storage.removeItem(key);
                }
            }
        }
    } catch (_error) {
        // Storage cleanup is best-effort only.
    }

    try {
        if (!window.indexedDB?.databases) {
            return;
        }
        const databases = await window.indexedDB.databases();
        await Promise.all((databases || []).map((database) => {
            const name = database?.name || "";
            if (!isWalletConnectStorageKey(name)) {
                return Promise.resolve();
            }
            return new Promise((resolve) => {
                const request = window.indexedDB.deleteDatabase(name);
                request.onsuccess = resolve;
                request.onerror = resolve;
                request.onblocked = resolve;
            });
        }));
    } catch (_error) {
        // IndexedDB cleanup is best-effort only.
    }
}

function isWalletConnectStorageKey(key) {
    const normalized = String(key || "").toLowerCase();
    return (
        normalized.includes("walletconnect")
        || normalized.includes("wallet_connect")
        || normalized.includes("wc@")
        || normalized.includes("wc_")
        || normalized.includes("w3m")
        || normalized.includes("reown")
        || normalized.includes("odoo_crypto_checkout")
    );
}

function walletErrorMessage(error) {
    const rawMessage = String(error?.message || error || "");
    if (rawMessage.includes("missing_walletconnect_project_id")) {
        return "WalletConnect Project ID is missing on the payment provider.";
    }
    if (rawMessage.includes("walletconnect_provider_not_loaded")) {
        return "WalletConnect could not be loaded. Please refresh and try again.";
    }
    const errorType = walletErrorType(error);
    if (errorType === "expired_request") {
        return "The wallet request expired. Please tap Pay with WalletConnect again and approve it in your wallet.";
    }
    if (errorType === "connection_timeout") {
        return "WalletConnect did not finish opening. Please tap Pay with WalletConnect again.";
    }
    if (errorType === "provider_reset") {
        return "WalletConnect session was interrupted. Please tap Pay with WalletConnect again.";
    }
    if (errorType === "cancelled") {
        return "Wallet request was cancelled. Please tap Pay with WalletConnect again when you are ready.";
    }
    if (errorType === "stale_session") {
        return "WalletConnect session was reset. Please tap Pay with WalletConnect again.";
    }
    if (error?.code === 4001 || rawMessage.toLowerCase().includes("user rejected")) {
        return "Wallet request was cancelled.";
    }
    return "WalletConnect payment failed. Please try again.";
}

function walletErrorType(error) {
    const rawMessage = String(error?.message || error || "");
    if (
        rawMessage.includes("Request expired")
        || rawMessage.toLowerCase().includes("request expired")
        || rawMessage.toLowerCase().includes("expired. please try again")
    ) {
        return "expired_request";
    }
    if (
        rawMessage.includes("walletconnect_connection_timeout")
        || rawMessage.includes("walletconnect_accounts_timeout")
        || rawMessage.includes("walletconnect_payment_timeout")
    ) {
        return "connection_timeout";
    }
    if (
        rawMessage.includes("Cannot read properties of undefined")
        && (rawMessage.includes("request") || rawMessage.includes("getDefaultChain"))
    ) {
        return "provider_reset";
    }
    if (
        rawMessage.toLowerCase().includes("user rejected")
        || rawMessage.toLowerCase().includes("rejected methods")
        || rawMessage.toLowerCase().includes("user denied")
        || rawMessage.includes("walletconnect_cancelled")
        || rawMessage.toLowerCase().includes("cancelled")
        || rawMessage.toLowerCase().includes("canceled")
        || rawMessage.toLowerCase().includes("modal closed")
    ) {
        return "cancelled";
    }
    if (
        rawMessage.includes("session topic doesn't exist")
        || rawMessage.includes("No matching key")
        || rawMessage.includes("No matching session")
    ) {
        return "stale_session";
    }
    return "";
}
