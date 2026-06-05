const BACKEND_URL = window.location.origin.includes('localhost') 
  ? 'http://localhost:8080' 
  : 'https://screamcasebot.onrender.com';

/**
 * Get initData from Telegram WebApp
 * CRITICAL: Every API request must include initData for server-side authentication
 */
const getInitData = () => {
  try {
    return window?.Telegram?.WebApp?.initData || '';
  } catch {
    return '';
  }
};

/**
 * Build fetch options with initData authentication
 */
const getAuthHeaders = () => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${getInitData()}`
});

/**
 * Build request body with initData
 */
const addAuthToBody = (body) => ({
  ...body,
  initData: getInitData()
});

/**
 * API Error Handler - Extracts error details from response
 */
const handleApiError = async (response) => {
  try {
    const errData = await response.json();
    return {
      status: response.status,
      error: errData.error || 'Unknown error',
      message: errData.message || '',
      ...errData
    };
  } catch {
    return {
      status: response.status,
      error: `Server error (${response.status})`,
      message: response.statusText || 'Unknown error'
    };
  }
};

/**
 * Show Telegram alert with proper error message
 */
const showAlert = (message) => {
  if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.showAlert(message);
  } else {
    alert(message);
  }
};

/**
 * Keep-alive ping to prevent Render hibernation
 * Вызывается каждые 10 минут из App.jsx
 */
export async function sendPing() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/ping`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    if (!response.ok) throw new Error(`Ping failed: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.warn('Keep-alive ping failed:', error);
    return null;
  }
}

/**
 * Format error message for display
 */
const formatErrorMessage = (errorData) => {
  const errorMessages = {
    'insufficient_funds': '❌ Недостаточно звёзд',
    'user_not_found': '❌ Пользователь не найден',
    'invalid_case': '❌ Неверный ID кейса',
    'minimum_donation_required': `❌ Требуется пожертвование минимум ${errorData.required || 0} звёзд`,
    'daily_cooldown_active': `❌ Ждите ${Math.ceil((errorData.wait_seconds || 86400) / 3600)} часов перед следующим открытием`,
    'transaction_already_processed': '❌ Эта транзакция уже обработана',
    'invalid_amount': '❌ Неверная сумма',
    'unauthorized': '❌ Вы не авторизованы',
    'invalid_data': '❌ Некорректные данные',
    'server_error': '❌ Ошибка сервера. Попробуйте позже',
    'already_completed': '❌ Задание уже выполнено',
    'task_not_found': '❌ Задание не найдено',
    'task_not_met': '❌ Условия задания не выполнены',
    'already_opened': '❌ Вы уже открывали этот кейс!',
    'case_limit_reached': '❌ Кейсы этого типа закончились!'
  };
  
  return errorMessages[errorData.error] || `❌ ${errorData.error || 'Ошибка'}`;
};

export const checkSubscription = async (userId) => {
  try {
    if (!userId) return false;
    const response = await fetch(`${BACKEND_URL}/api/check_sub?user_id=${userId}&initData=${encodeURIComponent(getInitData())}`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) return false;
    const data = await response.json();
    return data.is_subscribed || false;
  } catch (error) {
    console.error('Error checking subscription:', error);
    return false;
  }
};

export const fetchTasks = async (userId) => {
  try {
    if (!userId) return [];
    const response = await fetch(`${BACKEND_URL}/api/tasks?user_id=${userId}&initData=${encodeURIComponent(getInitData())}`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) return [];
    return await response.json();
  } catch (error) {
    console.error('Error fetching tasks:', error);
    return [];
  }
};

export const verifyTask = async (userId, taskId) => {
  try {
    if (!userId || !taskId) throw new Error('Missing user_id or task_id');
    const response = await fetch(`${BACKEND_URL}/api/tasks/verify`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(addAuthToBody({ user_id: userId, task_id: taskId })),
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      const message = formatErrorMessage(error);
      showAlert(message);
      throw new Error(message);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error verifying task:', error);
    if (!(error instanceof Error)) showAlert('❌ Ошибка при проверке задания');
    throw error;
  }
};

/**
 * ИСПРАВЛЕНО: Возвращает объект { stars, tickets, donor, spent, promo_opened }
 * Вызывающий код ДОЛЖЕН использовать data.stars, не сам data
 */
export const fetchBalance = async (userId) => {
  try {
    if (!userId) return { stars: 0, tickets: 0, donor: 0, spent: 0, promo_opened: 0 };
    
    const response = await fetch(`${BACKEND_URL}/api/balance?user_id=${userId}&initData=${encodeURIComponent(getInitData())}`, {
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      console.error('Balance fetch error:', error);
      return { stars: 0, tickets: 0, donor: 0, spent: 0, promo_opened: 0 };
    }
    
    const data = await response.json();
    // Возвращаем нормализованный объект — сервер присылает { ok, stars, tickets, donor, spent, promo_opened }
    return {
      stars: typeof data.stars === 'number' ? data.stars : 0,
      tickets: typeof data.tickets === 'number' ? data.tickets : 0,
      donor: typeof data.donor === 'number' ? data.donor : 0,
      spent: typeof data.spent === 'number' ? data.spent : 0,
      promo_opened: data.promo_opened || 0
    };
  } catch (error) {
    console.error('Error fetching balance:', error);
    return { stars: 0, tickets: 0, donor: 0, spent: 0, promo_opened: 0 };
  }
};

export const fetchReferrals = async (userId) => {
  try {
    if (!userId) return { count: 0, referrals: [] };
    
    const response = await fetch(`${BACKEND_URL}/api/referrals?user_id=${userId}&initData=${encodeURIComponent(getInitData())}`, {
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      console.error('Referrals fetch error:', error);
      return { count: 0, referrals: [] };
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching referrals:', error);
    return { count: 0, referrals: [] };
  }
};

export const spinWheel = async (userId) => {
  try {
    if (!userId) throw new Error('Missing user_id');
    
    const response = await fetch(`${BACKEND_URL}/api/wheel/spin`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(addAuthToBody({ user_id: userId })),
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      const message = formatErrorMessage(error);
      showAlert(message);
      
      const err = new Error(message);
      err.status = error.status;
      err.errorCode = error.error;
      throw err;
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error spinning wheel:', error);
    if (!(error instanceof Error) || !error.status) {
      showAlert('❌ Ошибка при прокруте колеса');
    }
    throw error;
  }
};

export const upgradeItem = async (userId, sourceInventoryId, targetName, targetPrice, targetImage = '') => {
  try {
    if (!userId) throw new Error('Missing user_id');
    
    const response = await fetch(`${BACKEND_URL}/api/upgrade`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(addAuthToBody({ user_id: userId, source_inventory_id: sourceInventoryId, target_name: targetName, target_price: targetPrice, target_image: targetImage })),
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      const message = formatErrorMessage(error);
      showAlert(message);
      throw new Error(message);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error upgrading item:', error);
    if (!(error instanceof Error)) {
      showAlert('❌ Ошибка при апгрейде');
    }
    throw error;
  }
};

export const fetchAchievements = async (userId) => {
  try {
    if (!userId) return [];
    const response = await fetch(`${BACKEND_URL}/api/achievements?user_id=${userId}&initData=${encodeURIComponent(getInitData())}`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) return [];
    return await response.json();
  } catch (error) {
    console.error('Error fetching achievements:', error);
    return [];  }
};

export const claimAchievement = async (userId, achievementId) => {
  try {
    if (!userId || !achievementId) throw new Error('Missing data');
    const response = await fetch(`${BACKEND_URL}/api/achievements/claim`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(addAuthToBody({ user_id: userId, achievement_id: achievementId })),
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      const message = formatErrorMessage(error);
      showAlert(message);
      throw new Error(message);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error claiming achievement:', error);
    throw error;
  }
};

export const createInvoice = async (userId, amount, paymentType = 'stars') => {
  try {
    if (!userId || !amount) {
      throw new Error('Missing userId or amount');
    }
    
    const endpoint = paymentType === 'stars' ? '/api/create_stars_invoice' : '/api/create_invoice';
    const response = await fetch(`${BACKEND_URL}${endpoint}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(addAuthToBody({ user_id: userId, amount, payment_type: paymentType })),
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      showAlert('❌ Ошибка при создании счёта');
      throw new Error(error.error || 'Failed to create invoice');
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error creating invoice:', error);
    throw error;
  }
};

export const notifyTonSuccess = async (userId, amount, txId) => {
  try {
    if (!userId || !amount || !txId) {
      throw new Error('Missing required parameters');
    }
    
    const response = await fetch(`${BACKEND_URL}/api/ton_success`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(addAuthToBody({ user_id: userId, amount, tx_id: txId })),
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      
      if (error.status === 400 && error.error === 'transaction_already_processed') {
        console.warn('TON transaction already processed');
        return { success: true, duplicate: true };
      }
      
      showAlert('❌ Ошибка при обработке платежа');
      throw new Error(error.error || 'TON payment failed');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error notifying TON success:', error);
    throw error;
  }
};

/**
 * Heartbeat - Keep Render.com server awake
 * Вызывается каждые 10 минут из App.jsx для предотвращения Render hibernation
 */
export const sendHeartbeat = async (userId) => {
  try {
    // Используем публичный /api/ping чтобы не упасть при отсутствии initData
    const response = await fetch(`${BACKEND_URL}/api/ping`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      console.warn('Heartbeat ping failed:', response.status);
      return { status: 'failed' };
    }
    
    const data = await response.json();
    console.log('💓 Heartbeat ping OK, сервер активен:', data.timestamp);
    return { status: 'success', ...data };
  } catch (error) {
    console.error('Error sending heartbeat:', error);
    return { status: 'error' };
  }
};

export const claimDaily = async (userId) => {
  try {
    if (!userId) {
      throw new Error('Missing userId');
    }
    
    const response = await fetch(`${BACKEND_URL}/api/open_case`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(addAuthToBody({ user_id: userId, case_id: 2 })),
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      
      if (error.status === 403 && error.error === 'daily_cooldown_active') {
        const message = `❌ Ждите ${Math.ceil((error.wait_seconds || 86400) / 3600)} часов`;
        showAlert(message);
        const err = new Error(message);
        err.status = 403;
        err.errorCode = 'daily_cooldown_active';
        err.waitSeconds = error.wait_seconds;
        throw err;
      }
      
      const message = formatErrorMessage(error);
      showAlert(message);
      
      const err = new Error(message);
      err.status = error.status;
      err.errorCode = error.error;
      throw err;
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error claiming daily:', error);
    if (!(error instanceof Error) || !error.status) {
      showAlert('❌ Ошибка при открытии ежедневного кейса');
    }
    throw error;
  }
};

export const openCase = async (userId, caseId, promoCode = null, quantity = 1) => {
  try {
    if (!userId || caseId === null) {
      throw new Error('Missing userId or caseId');
    }
    
    const payload = {
      user_id: userId,
      case_id: caseId,
      quantity: Math.max(1, Math.min(10, parseInt(quantity, 10) || 1)),
      ...(promoCode ? { promo_code: promoCode } : {})
    };
    
    const response = await fetch(`${BACKEND_URL}/api/open_case`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(addAuthToBody(payload)),
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);

      if (error.status === 403 && error.error === 'daily_cooldown_active') {
        const message = `❌ Ждите ${Math.ceil((error.wait_seconds || 86400) / 3600)} часов`;
        showAlert(message);
        const err = new Error(message);
        err.status = 403;
        err.errorCode = 'daily_cooldown_active';
        err.waitSeconds = error.wait_seconds;
        err.details = error;
        throw err;
      }

      const message = formatErrorMessage(error);
      showAlert(message);

      const err = new Error(message);
      err.status = error.status;
      err.errorCode = error.error;
      err.details = error;
      throw err;
    }

    return await response.json();
  } catch (error) {
    console.error('Error opening case:', error);
    if (!(error instanceof Error) || !error.status) {
      showAlert('❌ Ошибка при открытии кейса');
    }
    throw error;
  }
};

export const fetchQuests = async (userId) => {
  try {
    if (!userId) return [];
    const response = await fetch(`${BACKEND_URL}/api/quests?user_id=${userId}&initData=${encodeURIComponent(getInitData())}`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) return [];
    return await response.json();
  } catch (error) {
    console.error('Error fetching quests:', error);
    return [];
  }
};

export const claimQuest = async (userId, questId) => {
  try {
    if (!userId || !questId) throw new Error('Missing data');
    const response = await fetch(`${BACKEND_URL}/api/quests/claim`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(addAuthToBody({ user_id: userId, quest_id: questId })),
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      const message = formatErrorMessage(error);
      showAlert(message);
      throw new Error(message);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error claiming quest:', error);
    throw error;
  }
};

/**
 * ИСПРАВЛЕНО: одна единственная функция fetchCases (дубликат удалён)
 */
export const fetchCases = async () => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/cases`, {
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      console.error('Cases fetch error:', response.status);
      return [];
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching cases:', error);
    return [];
  }
};

export const fetchInventory = async (userId) => {
  try {
    if (!userId) return { user_id: userId, total_items: 0, total_value: 0, items: [] };
    
    const response = await fetch(`${BACKEND_URL}/api/inventory?user_id=${userId}&initData=${encodeURIComponent(getInitData())}`, {
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      console.error('Inventory fetch error:', response.status);
      return { user_id: userId, total_items: 0, total_value: 0, items: [] };
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching inventory:', error);
    return { user_id: userId, total_items: 0, total_value: 0, items: [] };
  }
};

export const redeemPromo = async (userId, code) => {
  try {
    if (!userId) throw new Error('Missing userId');
    if (!code || typeof code !== 'string') throw new Error('Invalid code');

    const cleanCode = code.trim().toUpperCase();

    const response = await fetch(`${BACKEND_URL}/api/redeem_promo`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(addAuthToBody({ user_id: userId, code: cleanCode })),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok || !data.success) {
      const errCode = data.error || 'unknown';
      const messages = {
        invalid_code: '❌ Неверный формат кода',
        code_not_found: '❌ Промокод не найден',
        code_expired: '❌ Промокод истёк',
        code_exhausted: '❌ Промокод больше недоступен',
        already_redeemed: '❌ Вы уже активировали этот код',
        user_not_found: '❌ Пользователь не найден',
        unauthorized: '❌ Нет авторизации',
        insufficient_deposit: `❌ Для активации пополните на ${data.required || '?'}⭐ (у вас ${data.have || 0}⭐ за 24ч)`,
      };
      let msg = messages[errCode] || '❌ Ошибка активации промокода';
      if (errCode === 'insufficient_deposit') {
        msg = `❌ Для активации пополните на ${data.required || '?'}⭐ (у вас ${data.have || 0}⭐ за 24ч)`;
      }
      showAlert(msg);
      const err = new Error(msg);
      err.status = response.status;
      err.errorCode = errCode;
      err.required = data.required;
      err.have = data.have;
      throw err;
    }

    return data; // { success, code, reward_stars, new_balance }
  } catch (error) {
    console.error('Error redeeming promo:', error);
    if (!error.status) {
      showAlert('❌ Ошибка сети. Попробуйте позже.');
    }
    throw error;
  }
};
