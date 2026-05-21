// Robust helper to get dynamic image from item object
export const DEFAULT_GIFT_IMAGE = '/asset/Gifts/Case.webp';

export function getDynamicGiftImage(item) {
  if (!item) return DEFAULT_GIFT_IMAGE;
  
  // Project requirement: files are named [NAME].webp (no price in filename)
  // Example: item.name = "Lol Pop" -> /asset/Gifts/Lol_Pop.webp
  let name = item.name || 'Gift';
  
  // 1. Remove any leading price prefixes like "15S_", "500S_", etc.
  name = name.replace(/^\d+S_/, '');
  
  // 2. Remove "Original" or other suffixes often added by backend helpers
  name = name.replace(/_Original.*/, '');
  
  // 3. Replace spaces with underscores for the filename consistency
  const formattedName = name.trim().replace(/\s+/g, '_');
  
  // 4. Return the requested path
  return `/asset/Gifts/${formattedName}.webp`;
}

export function normalizeGiftImage(image) {
  if (!image || typeof image !== 'string') return DEFAULT_GIFT_IMAGE;
  return image;
}

export const useDefaultGiftImage = (e) => {
  e.currentTarget.src = DEFAULT_GIFT_IMAGE;
};
