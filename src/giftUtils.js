export const DEFAULT_GIFT_IMAGE = '/asset/Gifts/Case.webp';

export function getDynamicGiftImage(item) {
  if (!item) return DEFAULT_GIFT_IMAGE;

  let name = item.name || 'Gift';

  name = name.replace(/^\d+S_/g, '');
  name = name.replace(/_Original.*/g, '');
  name = name.replace(/\s+/g, '_');

  const formattedName = name.trim().replace(/[^a-zA-Z0-9_]/g, '');

  return `/asset/Gifts/${formattedName}.webp`;
}

export function normalizeGiftImage(image) {
  if (!image || typeof image !== 'string') return DEFAULT_GIFT_IMAGE;
  return image;
}

export const handleImgError = (e) => {
  e.currentTarget.src = DEFAULT_GIFT_IMAGE;
  e.currentTarget.onerror = null;
};
