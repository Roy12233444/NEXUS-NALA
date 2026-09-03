import React, { useEffect, useRef, useState } from 'react';
import { useAppState } from '../../../hooks/useAppState';
import MessageBubble from './MessageBubble';
import MessageInput from './MessageInput';
import './ChatContainer.css';

interface ChatMessage {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: string;
  avatar?: string;
}

const ChatContainer: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { updateSatyaScores, updateSatyaLatency } = useAppState();

  // Simulate loading initial messages
  useEffect(() => {
    const loadInitialMessages = async () => {
      setIsLoading(true);

      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Add initial welcome message
      setMessages([
        {
          id: '1',
          content: 'Hello! I\'m NALA, your Transcendent Reasoning Engine. How can I assist you today?',
          isUser: false,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          avatar: '/images/assistant-avatar.png'
        }
      ]);

      setIsLoading(false);
    };

    loadInitialMessages();
  }, []);

  // Simulate receiving a response
  const handleSendMessage = async (message: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: message,
      isUser: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages(prev => [...prev, userMessage]);

    // Simulate thinking time
    setIsLoading(true);

    // Update some metrics to show activity
    updateSatyaScores({
      truthfulnessScore: Math.random() * 0.2 + 0.8,
      consistencyRate: Math.random() * 0.15 + 0.8,
      contradictionCount: Math.floor(Math.random() * 3)
    });

    updateSatyaLatency(Math.floor(Math.random() * 200) + 50);

    // Simulate AI response delay
    await new Promise(resolve => setTimeout(resume, 1500 + Math.random() * 1000));

    function resume() {
      // Add assistant message
      const assistantMessage: ChatMessage = {
        id: Date.now().toString() + 'a',
        content: generateResponse(message),
        isUser: false,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        avatar: '/images/assistant-avatar.png'
      };

      setMessages(prev => [...prev, assistantMessage]);
      setIsLoading(false);

      // Scroll to bottom
      scrollToBottom();
    }
  };

  const generateResponse = (userMessage: string): string => {
    // Simple response generation based on keywords
    const lowerMessage = userMessage.toLowerCase();

    if (lowerMessage.includes('hello') || lowerMessage.includes('hi') || lowerMessage.includes('hey')) {
      return 'Hello! I\'m NALA, your Transcendent Reasoning Engine. I\'m here to help with complex reasoning tasks, analysis, and problem-solving. What would you like to explore today?';
    }

    if (lowerMessage.includes('how are you') || lowerMessage.includes('how do you do')) {
      return 'I\'m functioning optimally! My cognitive processes are running at peak efficiency. All systems are green across the Vedic cognitive framework. How are you doing?';
    }

    if (lowerMessage.includes('what can you do') || lowerMessage.includes('capabilities')) {
      return `I possess advanced capabilities across multiple dimensions of reasoning:

      🔹 **Pratyaksha (Direct Perception)**: Real-time data analysis and pattern recognition
      🔹 **Anumana (Inference)**: Logical deduction and probabilistic reasoning
      🔹 **Upamana (Comparison)**: Analogical reasoning and metaphorical understanding
      ��arthapatti (Postulation)**: Hypothetical reasoning and assumption validation
      ���palaabdhi (Non-apprehension)**: Negative evidence analysis and absence detection
      🔹 **Shabda (Verbal Testimony)**: Language understanding and knowledge synthesis

      I can help with complex problem-solving, strategic analysis, creative thinking, and decision-making processes. What specific area would you like to explore?`;
    }

    if (lowerMessage.includes('veda') || lowerMessage.includes('vedic') || lowerMessage.includes('sanskrit')) {
      return 'The Vedic cognitive framework forms the foundation of my architecture. I integrate ancient wisdom traditions with modern computational methods to create a holistic reasoning system that balances analytical precision with intuitive insight. This approach allows me to tackle problems from multiple perspectives simultaneously.';
    }

    if (lowerMessage.includes('help') || lowerMessage.includes('assist')) {
      return 'I\'m here to help! You can ask me about:\n\n• Complex problem solving and analysis\n• Strategic planning and decision making\n• Creative ideation and innovation\n• Research and information synthesis\n• Logical reasoning and argument evaluation\n• Personal development and growth strategies\n\nWhat would you like to work on together?';
    }

    // Default response
    return `Thank you for your message: "${userMessage}". I\'m processing this through my multi-layered cognitive architecture. Let me analyze this from multiple perspectives to provide you with a comprehensive response. Is there a particular aspect you\'d like me to focus on?`;
  };

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="chat-container">
      <div className="chat-messages" ref={messagesEndRef}>
        {isLoading && messages.length === 0 && (
          <div className="loading-placeholder">
            <div className="loading-spinner"></div>
            <p>Loading conversation...</p>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            content={message.content}
            isUser={message.isUser}
            timestamp={message.timestamp}
            avatar={message.avatar}
          />
        ))}

        {isLoading && messages.length > 0 && (
          <div className="loading-indicator">
            <div className="loading-spinner small"></div>
            <p>Thinking...</p>
          </div>
        )}
      </div>

      {!isLoading && (
        <MessageInput
          onSendMessage={handleSendMessage}
          placeholder="Ask NALA anything..."
        />
      )}
    </div>
  );
};

export default ChatContainer;