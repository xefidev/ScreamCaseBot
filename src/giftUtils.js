import { ALL_GIFTS } from './giftData';

// Utility to parse gift filename: "1200S_Diamond Rings.png" → { price: 1200, name: "Diamond Rings", image: "/asset/Gifts/1200S_Diamond Rings.png" }

export function parseGiftFile(filename) {
  const match = filename.match(/^(\d+)S_(.+)\.png$/);
  if (!match) return null;
  return {
    price: parseInt(match[1]),
    name: match[2].replace(/_/g, ' '),
    image: `/asset/Gifts/${filename}`
  };
}

// Get gift asset by name - searches for image with pattern [Price]S_[Name].png in ALL_GIFTS
export function getFileAsset(giftName) {
  if (!ALL_GIFTS || ALL_GIFTS.length === 0) {
    console.warn(`getFileAsset: ALL_GIFTS is empty or undefined`);
    return `/asset/Gifts/15S_Bear.png`; // Fallback
  }

  // Find gift by name (case-insensitive)
  const gift = ALL_GIFTS.find(g => g.name.toLowerCase() === giftName.toLowerCase());
  
  if (!gift) {
    console.warn(`getFileAsset: Gift "${giftName}" not found in database`);
    // Try to find any gift that contains the name
    const partialMatch = ALL_GIFTS.find(g => g.name.toLowerCase().includes(giftName.toLowerCase()));
    if (partialMatch) return partialMatch.image;
    
    return `/asset/Gifts/15S_Bear.png`; // Hard fallback
  }

  return gift.image;
}

// Get gift asset by name - alias for getFileAsset
export function getGiftAsset(giftName) {
  return getFileAsset(giftName);
}
