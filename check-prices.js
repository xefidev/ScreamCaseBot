import { readdirSync } from 'fs';
import { join } from 'path';

const giftsDir = join(process.cwd(), 'public', 'asset', 'Gifts');
const files = readdirSync(giftsDir).filter(f => f.endsWith('.png'));

const prices = files.map(f => {
  const match = f.match(/^(\d+)S_(.+)\.png$/);
  if (match) {
    return parseInt(match[1]);
  }
  return null;
}).filter(x => x !== null);

const uniquePrices = [...new Set(prices)].sort((a, b) => a - b);

console.log('Total gifts:', files.length);
console.log('Min price:', Math.min(...prices));
console.log('Max price:', Math.max(...prices));
console.log('\nAll unique prices:');
console.log(uniquePrices.join(', '));
