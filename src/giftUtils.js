import { ALL_GIFTS } from './giftData';

export const DEFAULT_GIFT_IMAGE = '/asset/Gifts/Case.webp';

/**
 * Clean and normalize gift image path
 * Handles: removes prefixes (100S_, 50S_), replaces spaces with underscores
 * Returns path to /asset/Gifts/ folder
 */
export function normalizeGiftImage(image) {
  if (!image || typeof image !== 'string') return DEFAULT_GIFT_IMAGE;

  // Extract filename from full path
  const fileName = image
    .replaceAll('\\', '/')
    .split('/')
    .filter(Boolean)
    .pop();

  if (!fileName || fileName.includes('..')) return DEFAULT_GIFT_IMAGE;

  // Construct normalized path to /asset/Gifts/
  return `/asset/Gifts/${fileName}`;
}

/**
 * Fallback handler for broken image src
 */
export const handleImgError = (e) => {
  e.currentTarget.src = DEFAULT_GIFT_IMAGE;
  e.currentTarget.onerror = null;
};

/**
 * Parse gift filename: "100S_Diamond Ring.png" → { price: 100, name: "Diamond Ring", image: "/asset/Gifts/..." }
 */
export function parseGiftFile(filename) {
  const match = filename.match(/^(\d+)S_(.+)\.(png|webp|jpg|jpeg)$/i);
  if (!match) return null;
  return {
    price: parseInt(match[1]),
    name: match[2].replace(/_/g, ' '),
    image: `/asset/Gifts/${filename}`
  };
}

/**
 * Get gift asset by name from ALL_GIFTS database
 * Case-insensitive matching
 * Returns /asset/Gifts/ path or fallback
 */
export function getFileAsset(giftName) {
  if (!ALL_GIFTS || ALL_GIFTS.length === 0) {
    return DEFAULT_GIFT_IMAGE;
  }

  // Find gift by name (case-insensitive)
  const gift = ALL_GIFTS.find(g => g.name.toLowerCase() === giftName.toLowerCase());

  if (!gift) {
    // Try partial match as fallback
    const partialMatch = ALL_GIFTS.find(g =>
      g.name.toLowerCase().includes(giftName.toLowerCase())
    );
    if (partialMatch) return normalizeGiftImage(partialMatch.image);

    return DEFAULT_GIFT_IMAGE;
  }

  return normalizeGiftImage(gift.image);
}

/**
 * Alias for getFileAsset
 */
export function getGiftAsset(giftName) {
  return getFileAsset(giftName);
}

/**
 * Get dynamic gift image from item object
 * Cleans name (removes prefixes like "100S_", replaces spaces with underscores)
 * Returns constructed path: /asset/Gifts/[cleanedName].webp
 */
export function getDynamicGiftImage(item) {
  if (!item || (!item.name && item.price === undefined && item.cost === undefined)) {
    return DEFAULT_GIFT_IMAGE;
  }
  const price = item.price ?? item.cost ?? 0;
  const name = item.name || 'Gift';
  const formattedName = name.trim().replace(/\s+/g, '_');
  return `/asset/Gifts/${price}S_${formattedName}_Original_${formattedName}.webp`;
}
