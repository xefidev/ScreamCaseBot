const BACKEND_URL = 'https://screamcasebot.onrender.com';

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
 * Format error message for display
 */
const formatErrorMessage = (errorData) => {
  const errorMessages = {
    'insufficient_funds': '❌ Недостаточно средств',
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
    'task_not_met': '❌ Условия задания не выполнены'
  };
  
  return errorMessages[errorData.error] || `❌ ${errorData.error || 'Ошибка'}`;
};

export const checkSubscription = async (userId) => {
  try {
    if (!userId) return false;
    const response = await fetch(`${BACKEND_URL}/api/check_sub?user_id=${userId}`);
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
    const response = await fetch(`${BACKEND_URL}/api/tasks?user_id=${userId}`);
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, task_id: taskId }),
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

export const fetchBalance = async (userId) => {
  try {
    if (!userId) return { stars: 0, tickets: 0, donor: 0, spent: 0 };
    
    const response = await fetch(`${BACKEND_URL}/api/balance?user_id=${userId}`);
    
    if (!response.ok) {
      const error = await handleApiError(response);
      console.error('Balance fetch error:', error);
      return { stars: 0, tickets: 0, donor: 0, spent: 0 };
    }
    
    const data = await response.json();
    return {
      stars: data.stars || 0,
      tickets: data.tickets || 0,
      donor: data.donor || 0,
      spent: data.spent || 0
    };
  } catch (error) {
    console.error('Error fetching balance:', error);
    return { stars: 0, tickets: 0, donor: 0, spent: 0 };
  }
};

export const fetchReferrals = async (userId) => {
  try {
    if (!userId) return { count: 0, referrals: [] };
    
    const response = await fetch(`${BACKEND_URL}/api/referrals?user_id=${userId}`);
    
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
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

export const upgradeItem = async (userId, cost, chance) => {
  try {
    if (!userId) throw new Error('Missing user_id');
    
    const response = await fetch(`${BACKEND_URL}/api/upgrade`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, cost, chance }),
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

export const createInvoice = async (userId, amount) => {
  try {
    if (!userId || !amount) {
      throw new Error('Missing userId or amount');
    }
    
    const response = await fetch(`${BACKEND_URL}/api/create_invoice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, amount }),
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      showAlert('❌ Ошибка при создании счёта');
      throw new Error(error.error || 'Failed to create invoice');
    }
    
    return await response.json();
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, amount, tx_id: txId }),
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

export const claimDaily = async (userId) => {
  try {
    if (!userId) {
      throw new Error('Missing userId');
    }
    
    const response = await fetch(`${BACKEND_URL}/api/open_case`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, case_id: 2 }),
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

export const openCase = async (userId, caseId) => {
  try {
    if (!userId || caseId === null) {
      throw new Error('Missing userId or caseId');
    }
    
    const payload = {
      user_id: userId,
      case_id: caseId
    };
    
    const response = await fetch(`${BACKEND_URL}/api/open_case`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    
    if (!response.ok) {
      const error = await handleApiError(response);
      
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
