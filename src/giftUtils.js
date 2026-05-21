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
  
  // Try different possible price fields to avoid undefined
  const price = item.price ?? item.cost ?? item.reward ?? 0;
  
  // Handle names that might have spaces or underscores consistently
  // Project requirement: [PRICE]S_[NAME].webp
  let name = item.name || 'Gift';
  
  // Remove possible duplicate price prefix if it exists in the name string
  name = name.replace(/^\d+S_/, '');
  
  // Replace spaces with underscores for the filename
  const safeName = name.trim().replace(/\s+/g, '_');
  
  return `/asset/Gifts/${price}S_${safeName}.webp`;
}
