/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

let _inited = false;
let _pollingStarted = false;
let _walletConnectBound = false;
let _browserWalletBound = false;

function initCryptoPaymentPage() {
    if (_inited) {
        return;
    }
    _inited = true;

    const wrap = document.getElementById("wrap");
    if (!wrap) {
        return;
    }

    setupCopyButtons();

    const txId = parseInt(wrap.dataset.txId || "0", 10);
    const token = wrap.dataset.token || "";
    if (!txId || !token) {
        setWalletStatus("Missing payment session data.");
        return;
    }

    startCryptoPolling(txId, token);
    setupWalletConnect(txId, token, wrap.dataset.walletconnectProjectId || "");
    setupBrowserWallet(txId, token);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCryptoPaymentPage);
} else {
    initCryptoPaymentPage();
}

function setWalletStatus(text, alertClass = "") {
    const status = document.getElementById("wc_status");
    if (!status) {
        return;
    }
    status.className = alertClass || "text-muted mt-2";
    status.textContent = text || "";
}

function startCryptoPolling(txId, token) {
    if (_pollingStarted) {
        return;
    }
    _pollingStarted = true;

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
            setStatus("alert-info", "Waiting for payment confirmation...");
        } catch (_error) {
            setStatus("alert-warning", "Unable to check payment right now...");
        }
        setTimeout(poll, 2500);
    };

    poll();
}

function setupCopyButtons() {
    document.querySelectorAll("[data-copy]").forEach((btn) => {
        if (btn.dataset.copyBound === "1") {
            return;
        }
        btn.dataset.copyBound = "1";

        btn.addEventListener("click", async () => {
            const val = btn.getAttribute("data-copy") || "";
            try {
                await navigator.clipboard.writeText(val);
                const old = btn.textContent;
                btn.textContent = "Copied";
                setTimeout(() => (btn.textContent = old), 900);
            } catch (_error) {
                setWalletStatus("Copy failed. Please copy manually.", "text-warning mt-2");
            }
        });
    });
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
    if (window.ethereumProvider?.init) {
        return window.ethereumProvider;
    }
    return null;
}

async function getPaymentIntent(txId, token) {
    const intent = await rpc(`/crypto/intent/${txId}`, { token });
    if (!intent?.ok) {
        throw new Error(intent?.error || "payment_intent_error");
    }
    const chainId = Number(intent.chainId);
    const valueWeiStr = String(intent.valueWei || "0");
    return {
        chainId,
        to: intent.to,
        valueHex: `0x${BigInt(valueWeiStr).toString(16)}`,
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
        // The polling/webhook flow can still confirm payment if this helper route fails.
    }
}

async function sendPayment(provider, intent, txId, token, fromAddress) {
    const txHash = await provider.request({
        method: "eth_sendTransaction",
        params: [{
            from: fromAddress,
            to: intent.to,
            value: intent.valueHex,
            data: "0x",
        }],
    });
    await storeTransactionHash(txId, token, txHash, fromAddress);
    setWalletStatus(`Transaction sent: ${txHash}`, "text-success mt-2");
    return txHash;
}

function setupWalletConnect(txId, token, projectId) {
    if (_walletConnectBound) {
        return;
    }
    _walletConnectBound = true;

    const btn = document.getElementById("wc_connect_btn");
    const qrBox = document.getElementById("wc_qr_box");
    const hint = document.getElementById("wc_qr_hint");
    if (!btn) {
        return;
    }

    btn.addEventListener("click", async () => {
        const oldText = btn.textContent;
        btn.disabled = true;
        clearCustomQr(qrBox, hint);

        try {
            if (!projectId) {
                throw new Error("missing_walletconnect_project_id");
            }
            const EthereumProvider = getEthereumProvider();
            if (!EthereumProvider?.init) {
                throw new Error("walletconnect_provider_not_loaded");
            }

            btn.textContent = "Opening WalletConnect...";
            setWalletStatus("Preparing WalletConnect session...");
            const intent = await getPaymentIntent(txId, token);

            const provider = await EthereumProvider.init({
                projectId,
                chains: [intent.chainId],
                optionalChains: [intent.chainId],
                showQrModal: true,
                methods: ["eth_requestAccounts", "eth_accounts", "eth_sendTransaction"],
                events: ["accountsChanged", "chainChanged", "disconnect"],
                metadata: {
                    name: "Odoo Crypto Payment",
                    description: "Odoo crypto payment checkout",
                    url: window.location.origin,
                    icons: [`${window.location.origin}/web/image/website/1/favicon`],
                },
            });

            provider.on?.("display_uri", (uri) => renderCustomQr(uri, qrBox, hint));

            const accounts = await provider.enable();
            const from = accounts?.[0];
            if (!from) {
                throw new Error("walletconnect_no_account");
            }

            btn.textContent = "Approve payment in wallet...";
            setWalletStatus(`Connected: ${from}`);
            await sendPayment(provider, intent, txId, token, from);
            btn.textContent = "Transaction sent. Waiting confirmation...";
        } catch (error) {
            const message = walletErrorMessage(error);
            setWalletStatus(message, "text-warning mt-2");
            btn.disabled = false;
            btn.textContent = oldText;
        }
    });
}

function setupBrowserWallet(txId, token) {
    if (_browserWalletBound) {
        return;
    }
    _browserWalletBound = true;

    const btn = document.getElementById("metamask_pay_btn");
    if (!btn) {
        return;
    }
    if (!window.ethereum) {
        btn.disabled = true;
        btn.textContent = "Browser Wallet Not Found";
        return;
    }

    btn.addEventListener("click", async () => {
        const oldText = btn.textContent;
        btn.disabled = true;
        try {
            btn.textContent = "Connecting browser wallet...";
            const intent = await getPaymentIntent(txId, token);
            await ensureBrowserWalletChain(intent.chainId);
            const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
            const from = accounts?.[0];
            if (!from) {
                throw new Error("browser_wallet_no_account");
            }
            btn.textContent = "Approve payment in wallet...";
            await sendPayment(window.ethereum, intent, txId, token, from);
            btn.textContent = "Transaction sent. Waiting confirmation...";
        } catch (error) {
            setWalletStatus(walletErrorMessage(error), "text-warning mt-2");
            btn.disabled = false;
            btn.textContent = oldText;
        }
    });
}

async function ensureBrowserWalletChain(chainId) {
    const hexChainId = `0x${Number(chainId).toString(16)}`;
    try {
        await window.ethereum.request({
            method: "wallet_switchEthereumChain",
            params: [{ chainId: hexChainId }],
        });
    } catch (error) {
        if (error?.code === 4902) {
            throw new Error("chain_not_configured_in_wallet");
        }
        throw error;
    }
}

function renderCustomQr(uri, qrBox, hint) {
    if (!uri || !qrBox || typeof window.QRCode !== "function") {
        return;
    }
    qrBox.innerHTML = "";
    qrBox.style.display = "block";
    if (hint) {
        hint.style.display = "none";
    }
    new window.QRCode(qrBox, {
        text: uri,
        width: 280,
        height: 280,
    });
}

function clearCustomQr(qrBox, hint) {
    if (qrBox) {
        qrBox.innerHTML = "";
        qrBox.style.display = "none";
    }
    if (hint) {
        hint.style.display = "";
    }
}

function walletErrorMessage(error) {
    const rawMessage = String(error?.message || error || "");
    if (rawMessage.includes("missing_walletconnect_project_id")) {
        return "WalletConnect Project ID is missing on the payment provider.";
    }
    if (rawMessage.includes("walletconnect_provider_not_loaded")) {
        return "WalletConnect library is not loaded. Please refresh and try again.";
    }
    if (rawMessage.includes("chain_not_configured_in_wallet")) {
        return "This network is not configured in the browser wallet.";
    }
    if (error?.code === 4001 || rawMessage.toLowerCase().includes("user rejected")) {
        return "Wallet request was cancelled.";
    }
    return "Wallet payment failed. Please try again or use the QR/address fallback.";
}
