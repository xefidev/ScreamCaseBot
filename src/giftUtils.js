import { ALL_GIFTS } from './giftData';

export const DEFAULT_GIFT_IMAGE = '/asset/Gifts/default.webp';

export function normalizeGiftImage(image) {
  if (!image || typeof image !== 'string') return DEFAULT_GIFT_IMAGE;

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
    image: normalizeGiftImage(filename)
  };
}

// Get gift asset by name - searches for image with pattern [Price]S_[Name].png in ALL_GIFTS
export function getFileAsset(giftName) {
  if (!ALL_GIFTS || ALL_GIFTS.length === 0) {
    console.warn(`getFileAsset: ALL_GIFTS is empty or undefined`);
    return DEFAULT_GIFT_IMAGE;
  }

  // Find gift by name (case-insensitive)
  const gift = ALL_GIFTS.find(g => g.name.toLowerCase() === giftName.toLowerCase());
  
  if (!gift) {
    console.warn(`getFileAsset: Gift "${giftName}" not found in database`);
    // Try to find any gift that contains the name
    const partialMatch = ALL_GIFTS.find(g => g.name.toLowerCase().includes(giftName.toLowerCase()));
    if (partialMatch) return normalizeGiftImage(partialMatch.image);
    
    return DEFAULT_GIFT_IMAGE;
  }

  return normalizeGiftImage(gift.image);
}

// Get gift asset by name - alias for getFileAsset
export function getGiftAsset(giftName) {
  return getFileAsset(giftName);
}

// Robust helper to get dynamic image from item object
export function getDynamicGiftImage(item) {
  if (!item) return DEFAULT_GIFT_IMAGE;
  
  // Try to find by name first for "dynamic" binding as requested
  if (item.name) {
    const asset = getGiftAsset(item.name);
    if (asset !== DEFAULT_GIFT_IMAGE) return asset;
  }
  
  // Fallback to item.image if name search failed
  return normalizeGiftImage(item.image);
}
