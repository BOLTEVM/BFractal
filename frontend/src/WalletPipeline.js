import { TheGuardsWalletPipeline } from '../../../theguards';

/**
 * Fractal Bitcoin Wallet Pipeline
 * Native Web3 transaction execution pipeline for bfractal stack folder.
 * Handles Fractal Bitcoin & EVM layer-2 transactions via The Guards Scaffolding (WG-01..04).
 */
export class FractalWalletPipeline {
    /**
     * Executes a Fractal Bitcoin / EVM transaction and AWAITS on-chain block receipt verification.
     */
    static async executeAndAwaitTransaction(req) {
        console.log(`[FractalWalletPipeline] Executing Fractal Bitcoin transaction to ${req.to}...`);

        return TheGuardsWalletPipeline.executeAndAwaitTransaction({
            to: req.to,
            from: req.from,
            data: req.data,
            value: req.value,
            gasLimit: req.gasLimit,
            chainId: req.chainId,
            rpcUrl: req.rpcUrl || 'http://127.0.0.1:8000',
            provider: req.provider,
            confirmations: req.confirmations,
            timeoutMs: req.timeoutMs
        });
    }

    static async ensureChain(provider, chainId, rpcUrl) {
        return TheGuardsWalletPipeline.ensureChain(provider, chainId, rpcUrl);
    }
}
