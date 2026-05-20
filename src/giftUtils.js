import { ALL_GIFTS } from './giftData';

export const DEFAULT_GIFT_IMAGE = '/asset/Gifts/default.webp';

export function normalizeGiftImage(image) {
  if (!image || typeof image !== 'string') return DEFAULT_GIFT_IMAGE;

  // Pattern: [price]_[name].png in flat folder /images/gifts/
  // We use this pattern for all images now as requested
  const fileName = image
    .replaceAll('\\', '/')
    .split('/')
    .filter(Boolean)
    .pop();

  if (!fileName || fileName.includes('..')) return DEFAULT_GIFT_IMAGE;
  
  // Map to the new flat folder location
  return `/images/gifts/${fileName}`;
}

export function useDefaultGiftImage(event) {
  if (event.currentTarget.src.endsWith(DEFAULT_GIFT_IMAGE)) return;
  event.currentTarget.src = DEFAULT_GIFT_IMAGE;
}

export function parseGiftFile(filename) {
  const match = filename.match(/^(\d+)_(.+)\.(png|webp|jpg|jpeg)$/i);
  if (!match) return null;
  return {
    price: parseInt(match[1]),
    name: match[2].replace(/_/g, ' '),
    image: `/images/gifts/${filename}`
  };
}

// Get gift asset by name - searches for image with pattern [Price]_[Name].png in ALL_GIFTS
export function getFileAsset(giftName) {
  if (!ALL_GIFTS || ALL_GIFTS.length === 0) {
    return DEFAULT_GIFT_IMAGE;
  }

  const gift = ALL_GIFTS.find(g => g.name.toLowerCase() === giftName.toLowerCase());
  
  if (!gift) {
    return DEFAULT_GIFT_IMAGE;
  }

  // Construct filename dynamically based on price and name
  const safeName = gift.name.toLowerCase().replace(/\s+/g, '_');
  return `/images/gifts/${gift.price}_${safeName}.png`;
}

// Get gift asset by name - alias for getFileAsset
export function getGiftAsset(giftName) {
  return getFileAsset(giftName);
}

// Robust helper to get dynamic image from item object
export function getDynamicGiftImage(item) {
  if (!item) return DEFAULT_GIFT_IMAGE;
  
  const price = item.price || 0;
  const name = (item.name || 'gift').toLowerCase().replace(/\s+/g, '_');
  
  // Return the dynamic path pattern [price]_[name].png in flat folder
  return `/images/gifts/${price}_${name}.png`;
}
