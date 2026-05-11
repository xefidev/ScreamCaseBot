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

export const fetchLeaderboard = async () => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/leaderboard`);
    if (!response.ok) throw new Error('Failed to fetch leaderboard');
    return await response.json();
  } catch (error) {
    console.error('Error fetching leaderboard:', error);
    return [];
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

export const adminCreatePromo = async (adminId, promoData) => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/admin/create_promo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_id: adminId, ...promoData }),
    });
    if (!response.ok) throw new Error('Failed to create promo');
    return await response.json();
  } catch (error) {
    console.error('Error creating promo:', error);
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

export const notifyTonSuccess = async (userId, amount) => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/ton_success`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, amount }),
    });
    if (!response.ok) throw new Error('Failed to notify TON success');
    return await response.json();
  } catch (error) {
    console.error('Error notifying TON success:', error);
    throw error;
  }
};

export const openCase = async (userId, caseId, price) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/open_case`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, case_id: caseId, price }),
      });
      if (!response.ok) throw new Error('Insufficient funds or error');
      return await response.json();
    } catch (error) {
      console.error('Error opening case:', error);
      throw error;
    }
  };
