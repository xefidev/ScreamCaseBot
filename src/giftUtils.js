import { ALL_GIFTS } from './giftData';

export const DEFAULT_GIFT_IMAGE = '/asset/Case/CaseBlack.png';

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
 * Cleans name (removes apostrophes, replaces spaces/special symbols with underscores)
 * Returns constructed path: /asset/Gifts/[price]S_[formattedName]_Original_[formattedName].webp
 */
export function getDynamicGiftImage(item) {
  if (!item || (!item.name && item.price === undefined && item.cost === undefined)) {
    return DEFAULT_GIFT_IMAGE;
  }

  // Маппинг для исправления несовпадений имен/цен в базе и на диске
  const nameMap = {
    'Bear': { price: 2, name: 'Polar_Bear' },
    'Rosae': { price: 200, name: 'Roses' },
    'Lol Pops': { price: 450, name: 'Lol_Pop' },
    'Flowers': { price: 1008, name: 'Sakura_Flower' },
    'Cake': { price: 537, name: 'Mousse_Cake' },
    'GiftBox': { price: 500, name: 'Tama_Gadget' },
    'Instant Ramens': { price: 370, name: 'Instant_Ramen' },
    'Xmas Stockings': { price: 325, name: 'Xmas_Stocking' },
    'Spring Baskets': { price: 615, name: 'Spring_Basket' },
    'Swag Bags': { price: 520, name: 'Swag_Bag' },
    'Winter Wreaths': { price: 370, name: 'Winter_Wreath' },
    'Jester Hats': { price: 420, name: 'Jester_Hat' },
    'Hex Pots': { price: 474, name: 'Hex_Pot' },
    'Easter Eggs': { price: 420, name: 'Easter_Egg' },
    'Pool Floats': { price: 243, name: 'Pool_Float' },
    'Restless Jars': { price: 550, name: 'Restless_Jar' },
    'Witch Hats': { price: 550, name: 'Witch_Hat' },
    'Magic Potions': { price: 1258, name: 'Magic_Potion' },
    'Snoop Cigars': { price: 1188, name: 'Snoop_Cigar' },
    'Desk Calendars': { price: 640, name: 'Desk_Calendar' },
    'Love Potions': { price: 928, name: 'Love_Potion' },
    'Fresh Socks': { price: 615, name: 'Fresh_Socks' },
    'Westside Signs': { price: 5000, name: 'Westside_Sign' },
    'Top Hats': { price: 699, name: 'Top_Hat' },
    'Vice Creams': { price: 250, name: 'Vice_Cream' },
    'Ice Creams': { price: 399, name: 'Ice_Cream' },
    'Jolly Chimps': { price: 928, name: 'Jolly_Chimp' },
    'Sakura Flowers': { price: 1008, name: 'Sakura_Flower' },
    'Swiss Watches': { price: 5284, name: 'Swiss_Watch' },
    'Input Keys': { price: 600, name: 'Input_Key' },
    'Scared Cats': { price: 2506, name: 'Scared_Cat' },
    'Clover Pins': { price: 500, name: 'Clover_Pin' },
    'Lush Bouquets': { price: 535, name: 'Lush_Bouquet' },
    'Victory Medals': { price: 2300, name: 'Victory_Medal' },
    'Hypno Lollipops': { price: 500, name: 'Hypno_Lollipop' },
    'Valentine Boxes': { price: 920, name: 'Valentine_Box' },
    'Voodoo Dolls': { price: 3234, name: 'Voodoo_Doll' },
    'Heroic Helmets': { price: 26372, name: 'Heroic_Helmet' },
    'Cookie Hearts': { price: 549, name: 'Cookie_Heart' },
    'Moon Pendants': { price: 632, name: 'Moon_Pendant' },
    'Trapped Hearts': { price: 500, name: 'Trapped_Heart' },
    'Snake Boxes': { price: 400, name: 'Snake_Box' },
    'Tama Gadgets': { price: 500, name: 'Tama_Gadget' },
    'Bunny Muffins': { price: 500, name: 'Bunny_Muffin' },
    'Faith Amulets': { price: 1057, name: 'Faith_Amulet' },
    'Bonded Rings': { price: 4361, name: 'Bonded_Ring' },
    'Timeless Books': { price: 570, name: 'Timeless_Book' },
    'Crystal Balls': { price: 17230, name: 'Crystal_Ball' },
    'Holiday Drinks': { price: 369, name: 'Holiday_Drink' },
    'Vintage Cigars': { price: 400, name: 'Vintage_Cigar' },
    'Artisan Bricks': { price: 7922, name: 'Artisan_Brick' },
    'Electric Skulls': { price: 3000, name: 'Electric_Skull' },
    'Gem Signets': { price: 2755, name: 'Gem_Signet' },
    'Neko Helmets': { price: 5000, name: 'Neko_Helmet' },
    'Diamond Rings': { price: 7942, name: 'Diamond_Ring' },
    'Heart Lockets': { price: 928, name: 'Heart_Locket' },
    'Astral Shards': { price: 10130, name: 'Astral_Shard' },
    'Signet Rings': { price: 3299, name: 'Signet_Ring' },
    'Skull Flowers': { price: 1007, name: 'Skull_Flower' },
    'Ion Gems': { price: 950, name: 'Ion_Gem' },
    'Party Sparklers': { price: 398, name: 'Party_Sparkler' },
    'Berry Boxes': { price: 1050, name: 'Berry_Box' },
    'Cupid Charms': { price: 1960, name: 'Cupid_Charm' },
    'Mighty Arms': { price: 7953, name: 'Mighty_Arm' },
    'Santa Hats': { price: 413, name: 'Santa_Hat' },
    'Sky Stilettos': { price: 1339, name: 'Sky_Stilettos' },
    'Rare Birds': { price: 7500, name: 'Rare_Bird' },
    'Snow Mittens': { price: 563, name: 'Snow_Mittens' },
    'Mood Packs': { price: 350, name: 'Mood_Pack' },
    'Light Swords': { price: 678, name: 'Light_Sword' },
    'Big Years': { price: 560, name: 'Big_Year' },
    'Hanging Stars': { price: 620, name: 'Hanging_Star' },
    'Record Players': { price: 1027, name: 'Record_Player' },
    'Jingle Bells': { price: 928, name: 'Jingle_Bells' },
    'Mini Oscars': { price: 2500, name: 'Mini_Oscar' },
    'Spy Agarics': { price: 627, name: 'Spy_Agaric' },
    'Sleigh Bells': { price: 960, name: 'Sleigh_Bell' },
    'Loot Bags': { price: 890, name: 'Loot_Bag' },
    'Precious Peaches': { price: 3500, name: 'Precious_Peach' },
    'Kissed Frogs': { price: 5039, name: 'Kissed_Frog' },
    'Mad Pumpkins': { price: 1074, name: 'Mad_Pumpkin' },
    'Ionic Dryers': { price: 1050, name: 'Ionic_Dryer' },
    'Money Pots': { price: 495, name: 'Money_Pot' },
    'Flying Brooms': { price: 1075, name: 'Flying_Broom' },
    'Toy Bears': { price: 900, name: 'Toy_Bear' },
    'Genie Lamps': { price: 4768, name: 'Genie_Lamp' },
    'Low Riders': { price: 5233, name: 'Low_Rider' },
    'Nail Bracelets': { price: 3705, name: 'Nail_Bracelet' },
    'Stellar Rockets': { price: 476, name: 'Stellar_Rocket' }
  };

  let finalName = item.name || 'Gift';
  let finalPrice = item.price ?? item.cost ?? 0;

  if (nameMap[finalName]) {
    finalPrice = nameMap[finalName].price;
    finalName = nameMap[finalName].name;
  }
  
  // Clean name logic: 
  // 1. Remove apostrophes
  // 2. Replace all non-alphanumeric characters (spaces, hyphens, etc) with "_"
  const cleanedName = finalName.trim()
    .replace(/'/g, '')
    .replace(/[^a-zA-Z0-9]/g, '_')
    .replace(/_+/g, '_'); // Ensure single underscore

  return `/asset/Gifts/${finalPrice}S_${cleanedName}_Original_${cleanedName}.webp`;
}
