export const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
  
  if (diffInMinutes < 1) {
    return 'Just now';
  } else if (diffInMinutes < 60) {
    return `${diffInMinutes}m ago`;
  } else if (diffInMinutes < 1440) {
    return `${Math.floor(diffInMinutes / 60)}h ago`;
  } else {
    return date.toLocaleDateString();
  }
};

export const generateMessageId = (): string => {
  return Date.now().toString() + Math.random().toString(36).substr(2, 9);
};

export const detectUrls = (text: string): string[] => {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  return text.match(urlRegex) || [];
};

export const isGifUrl = (url: string): boolean => {
  return url.includes('giphy.com') || url.endsWith('.gif');
};

export const sanitizeMessage = (message: string): string => {
  return message
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
};

export const playNotificationSound = () => {
  if ('AudioContext' in window || 'webkitAudioContext' in window) {
    const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
    const audioContext = new AudioContext();
    
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.value = 800;
    oscillator.type = 'sine';
    
    gainNode.gain.setValueAtTime(0, audioContext.currentTime);
    gainNode.gain.linearRampToValueAtTime(0.2, audioContext.currentTime + 0.01);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.4);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.4);
  }
};

export const getPlayerStatusColor = (status: string): string => {
  switch (status) {
    case 'online':
      return 'text-green-400';
    case 'in-game':
      return 'text-yellow-400';
    case 'away':
      return 'text-gray-400';
    default:
      return 'text-green-400';
  }
};

export const generateBotResponse = (lastMessages: string[], playerName: string): string => {
  const responses = [
    `Hey ${playerName}! How's the game going?`,
    "Need any tips or strategies? I'm here to help!",
    "What's your favorite part of the game so far?",
    "I noticed you've been quiet. Everything okay?",
    "Ready for the next challenge?",
    "That was an impressive move! Keep it up!",
    "Want to try a different strategy?",
    "How are you finding the difficulty level?",
  ];
  
  return responses[Math.floor(Math.random() * responses.length)];
};