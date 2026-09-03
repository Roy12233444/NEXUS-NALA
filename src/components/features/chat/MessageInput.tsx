import React, { useState, useRef } from 'react';
import { useAppState } from '../../../hooks/useAppState';
import './MessageInput.css';

interface MessageInputProps {
  onSendMessage: (message: string) => Promise<void> | void;
  placeholder?: string;
  disabled?: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  placeholder = 'Type a message...',
  disabled = false,
}) => {
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { updateRitaScore } = useAppState();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputValue.trim() || isSending || disabled) return;

    setIsSending(true);
    try {
      await onSendMessage(inputValue);
      setInputValue('');

      // Simulate updating Rita score based on interaction
      updateRitaScore(Math.min(0.95, Math.random() * 0.2 + 0.8));
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.TextareaEventHandler<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
  };

  const handleTextAreaChange = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  return (
    <form className="message-input-form" onSubmit={handleSubmit}>
      <div className="message-input-container">
        <textarea
          ref={textareaRef}
          className="message-input"
          placeholder={placeholder}
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onInput={handleTextAreaChange}
          rows={1}
          maxRows={5}
          disabled={disabled}
        />
        <div className="message-input-actions">
          {!isSending && (
            <button
              type="button"
              className="voice-button"
              onClick={() => {
                // Voice input functionality would go here
                console.log('Voice input clicked');
              }}
              disabled={disabled}
            >
              <span className="voice-icon">🎤</span>
            </button>
          )}
          {isSending && (
            <div className="sending-indicator">
              <span className="sending-dot"></span>
              <span className="sending-dot"></span>
              <span className="sending-dot"></span>
            </div>
          )}
          <button
            type="submit"
            className={`send-button ${isSending ? 'sending' : ''}`}
            disabled={disabled || !inputValue.trim() || isSending}
          >
            {isSending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </form>
  );
};

export default MessageInput;