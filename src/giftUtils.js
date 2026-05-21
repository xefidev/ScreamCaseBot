import { ALL_GIFTS } from './giftData';

export const DEFAULT_GIFT_IMAGE = '/asset/Gifts/Case.webp';

export function normalizeGiftImage(image) {
  if (!image || typeof image !== 'string') return DEFAULT_GIFT_IMAGE;

  // Pattern: [price]S_[name].webp in folder /asset/Gifts/
  const fileName = image
    .replaceAll('\\', '/')
    .split('/')
    .filter(Boolean)
    .pop();

  if (!fileName || fileName.includes('..')) return DEFAULT_GIFT_IMAGE;
  
  return `/asset/Gifts/${fileName}`;
}

export function useDefaultGiftImage(event) {
  if (event.currentTarget.src.endsWith(DEFAULT_GIFT_IMAGE)) return;
  event.currentTarget.src = DEFAULT_GIFT_IMAGE;
}

export function parseGiftFile(filename) {
  const match = filename.match(/^(\d+)S_(.+)\.(png|webp|jpg|jpeg)$/i);
  if (!match) return null;
  return {
    price: parseInt(match[1]),
    name: match[2].replace(/_/g, ' '),
    image: `/asset/Gifts/${filename}`
  };
}

// Get gift asset by name - searches for image with pattern [Price]S_[Name].webp
export function getFileAsset(giftName, price = 0) {
  // Construct filename dynamically based on price and name
  const safeName = (giftName || '').replace(/\s+/g, '_');
  // Use .webp as primary as requested, but logic can handle others via error fallback
  return `/asset/Gifts/${price}S_${safeName}.webp`;
}

// Get gift asset by name - alias for getFileAsset
export function getGiftAsset(giftName, price = 0) {
  return getFileAsset(giftName, price);
}

// Robust helper to get dynamic image from item object
export function getDynamicGiftImage(item) {
  if (!item) return DEFAULT_GIFT_IMAGE;
  
  // Project requirement: files are named [NAME].webp (no price in filename)
  // Path MUST be /asset/Gifts/[NAME].webp
  let name = item.name || 'Gift';
  
  // 1. Remove any leading price prefixes like "15S_", "500S_", etc.
  name = name.replace(/^\d+S_/, '');
  
  // 2. Remove "Original" or other suffixes if they exist in the name
  name = name.replace(/_Original.*/, '');
  
  // 3. Replace spaces with underscores for the filename consistency
  const formattedName = name.trim().replace(/\s+/g, '_');
  
  // 4. Return the requested path
  return `/asset/Gifts/${formattedName}.webp`;
}
