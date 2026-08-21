import React from "react";
import { CreditCard, CheckCircle2, XCircle } from "lucide-react";

export default function TransactionsPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Financial Transactions</h1>
        <p className="text-sm text-slate-400">
          Ledger of executed operations through the Razorpay payment gateway.
        </p>
      </div>

      <div className="rounded-xl bg-[#111827] border border-[#1f293d] overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900/60 text-slate-400 text-xs uppercase font-mono border-b border-[#1f293d]">
            <tr>
              <th className="px-6 py-4">Transaction ID</th>
              <th className="px-6 py-4">Operation</th>
              <th className="px-6 py-4">Amount</th>
              <th className="px-6 py-4">Gateway Reference</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1f293d] text-slate-300">
            {[
              { id: "tx_99812", op: "CREATE_ORDER", amount: "₹ 15,000", rzpId: "order_mock_49f82d1", status: "CAPTURED", time: "10 mins ago" },
              { id: "tx_99811", op: "CREATE_REFUND", amount: "₹ 1,200", rzpId: "rfnd_mock_11e74a8", status: "REFUNDED", time: "1 hour ago" },
              { id: "tx_99810", op: "CREATE_PAYMENT_LINK", amount: "₹ 4,500", rzpId: "plink_mock_38cb091", status: "CREATED", time: "3 hours ago" },
            ].map((tx) => (
              <tr key={tx.id} className="hover:bg-slate-800/20">
                <td className="px-6 py-4 font-mono text-xs text-blue-400">{tx.id}</td>
                <td className="px-6 py-4 font-medium text-white">{tx.op}</td>
                <td className="px-6 py-4 font-mono font-semibold text-slate-100">{tx.amount}</td>
                <td className="px-6 py-4 font-mono text-xs text-slate-400">{tx.rzpId}</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <CheckCircle2 className="h-3 w-3" />
                    {tx.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-xs text-slate-500">{tx.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
