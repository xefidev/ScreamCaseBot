const BACKEND_URL = 'https://screamcasebot.onrender.com';

export const fetchBalance = async (userId) => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/balance?user_id=${userId}`);
    if (!response.ok) throw new Error('Failed to fetch balance');
    const data = await response.json();
    return data.stars || 0;
  } catch (error) {
    console.error('Error fetching balance:', error);
    return 0;
  }
};

export const fetchDailyInfo = async (userId) => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/daily_info?user_id=${userId}`);
    if (!response.ok) throw new Error('Failed to fetch daily info');
    return await response.json();
  } catch (error) {
    console.error('Error fetching daily info:', error);
    return { status: 'error' };
  }
};

export const claimDaily = async (userId) => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/claim_daily`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    if (!response.ok) throw new Error('Failed to claim daily');
    return await response.json();
  } catch (error) {
    console.error('Error claiming daily:', error);
    throw error;
  }
};

export const claimPromo = async (userId, code) => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/claim_promo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, code }),
    });
    if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.message || errData.error || 'Failed to claim promo');
    }
    return await response.json();
  } catch (error) {
    console.error('Error claiming promo:', error);
    throw error;
  }
};

export const createInvoice = async (userId, amount) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/create_invoice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, amount }),
      });
      if (!response.ok) throw new Error('Failed to create invoice');
      return await response.json();
    } catch (error) {
      console.error('Error creating invoice:', error);
      throw error;
    }
  };

export const addStars = async (userId, amount) => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/add_stars`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, amount }),
    });
    if (!response.ok) throw new Error('Failed to add stars');
    const data = await response.json();
    return data.new_balance;
  } catch (error) {
    console.error('Error adding stars:', error);
    throw error;
  }
};

export const openCase = async (userId, caseId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/open_case`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, case_id: caseId }),
      });
      if (!response.ok) throw new Error('Failed to open case');
      return await response.json();
    } catch (error) {
      console.error('Error opening case:', error);
      throw error;
    }
  };
