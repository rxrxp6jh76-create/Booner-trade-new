import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { X } from 'lucide-react';

const TradesTable = ({ trades, onCloseTrade }) => {
  if (!trades || trades.length === 0) {
    return (
      <div className="text-center text-slate-500 py-8">
        Noch keine Trades vorhanden
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="border-slate-700 hover:bg-slate-800/50">
            <TableHead className="text-slate-400">Zeit</TableHead>
            <TableHead className="text-slate-400">Typ</TableHead>
            <TableHead className="text-slate-400">Einstiegspreis</TableHead>
            <TableHead className="text-slate-400">Menge</TableHead>
            <TableHead className="text-slate-400">SL</TableHead>
            <TableHead className="text-slate-400">TP</TableHead>
            <TableHead className="text-slate-400">Status</TableHead>
            <TableHead className="text-slate-400">Ausstiegspreis</TableHead>
            <TableHead className="text-slate-400">P/L</TableHead>
            <TableHead className="text-slate-400">Modus</TableHead>
            <TableHead className="text-slate-400">Aktion</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map((trade) => (
            <TableRow key={trade.id} className="border-slate-700 hover:bg-slate-800/30" data-testid={`trade-row-${trade.id}`}>
              <TableCell className="text-slate-300">
                {new Date(trade.timestamp).toLocaleString('de-DE', {
                  day: '2-digit',
                  month: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </TableCell>
              <TableCell>
                <Badge 
                  className={trade.type === 'BUY' ? 'bg-emerald-600' : 'bg-rose-600'}
                  data-testid={`trade-type-${trade.id}`}
                >
                  {trade.type}
                </Badge>
              </TableCell>
              <TableCell className="text-slate-300">${trade.entry_price.toFixed(2)}</TableCell>
              <TableCell className="text-slate-300">{trade.quantity}</TableCell>
              <TableCell className="text-amber-400">
                {trade.stop_loss ? `$${trade.stop_loss.toFixed(2)}` : '-'}
              </TableCell>
              <TableCell className="text-emerald-400">
                {trade.take_profit ? `$${trade.take_profit.toFixed(2)}` : '-'}
              </TableCell>
              <TableCell>
                <Badge 
                  className={trade.status === 'OPEN' ? 'bg-blue-600' : 'bg-slate-600'}
                  data-testid={`trade-status-${trade.id}`}
                >
                  {trade.status}
                </Badge>
              </TableCell>
              <TableCell className="text-slate-300">
                {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : '-'}
              </TableCell>
              <TableCell className={trade.profit_loss ? (trade.profit_loss > 0 ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold') : 'text-slate-500'}>
                {trade.profit_loss ? `$${trade.profit_loss.toFixed(2)}` : '-'}
              </TableCell>
              <TableCell>
                <Badge variant="outline" className="border-slate-600 text-slate-300">
                  {trade.mode}
                </Badge>
              </TableCell>
              <TableCell>
                {trade.status === 'OPEN' && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onCloseTrade(trade.id)}
                    className="hover:bg-rose-600/20 text-rose-400"
                    data-testid={`close-trade-${trade.id}`}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default TradesTable;