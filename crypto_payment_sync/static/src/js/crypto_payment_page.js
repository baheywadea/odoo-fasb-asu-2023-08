/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

let inited = false;
let pollingStarted = false;
let walletConnectBound = false;

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
            setStatus("alert-info", "Waiting for payment confirmation...");
        } catch (_error) {
            setStatus("alert-warning", "Unable to check payment right now...");
        }
        setTimeout(poll, 2500);
    };

    poll();
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
        const oldText = btn.textContent;
        btn.disabled = true;

        try {
            if (!projectId) {
                throw new Error("missing_walletconnect_project_id");
            }

            btn.textContent = "Opening WalletConnect...";
            setWalletStatus("Preparing WalletConnect session...");

            const [EthereumProvider, intent] = await Promise.all([
                loadEthereumProvider(),
                getPaymentIntent(txId, token),
            ]);
            if (!EthereumProvider?.init) {
                throw new Error("walletconnect_provider_not_loaded");
            }

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

            const accounts = await provider.enable();
            const from = accounts?.[0];
            if (!from) {
                throw new Error("walletconnect_no_account");
            }

            btn.textContent = "Approve payment in wallet...";
            setWalletStatus(`Connected: ${from}`);

            const txHash = await provider.request({
                method: "eth_sendTransaction",
                params: [{
                    from,
                    to: intent.to,
                    value: intent.valueHex,
                    data: "0x",
                }],
            });
            await storeTransactionHash(txId, token, txHash, from);

            setWalletStatus(`Transaction sent: ${txHash}`, "text-success mt-2");
            btn.textContent = "Transaction sent. Waiting confirmation...";
        } catch (error) {
            setWalletStatus(walletErrorMessage(error), "text-warning mt-2");
            btn.disabled = false;
            btn.textContent = oldText;
        }
    });
}

function walletErrorMessage(error) {
    const rawMessage = String(error?.message || error || "");
    if (rawMessage.includes("missing_walletconnect_project_id")) {
        return "WalletConnect Project ID is missing on the payment provider.";
    }
    if (rawMessage.includes("walletconnect_provider_not_loaded")) {
        return "WalletConnect could not be loaded. Please refresh and try again.";
    }
    if (error?.code === 4001 || rawMessage.toLowerCase().includes("user rejected")) {
        return "Wallet request was cancelled.";
    }
    return "WalletConnect payment failed. Please try again.";
}
