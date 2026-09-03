import React from 'react';
import './MessageBubble.css';

interface MessageBubbleProps {
  content: string;
  isUser: boolean;
  timestamp?: string;
  avatar?: string;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
  content,
  isUser,
  timestamp,
  avatar,
}) => {
  return (
    <div className={`message-bubble ${isUser ? 'user-message' : 'assistant-message'}`}>
      {avatar && !isUser && (
        <img src={avatar} alt="Assistant" className="message-avatar" />
      )}
      <div className="message-content">
        <div className="message-text">{content}</div>
        {timestamp && (
          <div className="message-timestamp">{timestamp}</div>
        )}
      </div>
      {!isUser && avatar && (
        <img src={avatar} alt="Assistant" className="message-avatar" />
      )}
    </div>
  );
};

export default MessageBubble;