import React from 'react';
import { IconFile, IconImage, IconX, IconDatabase, IconClipboard } from './LucideIcons';
import './Attachments.css';

export interface AttachmentMeta {
  id?: string;
  type: 'image' | 'file';
  name: string;
  url?: string;
  mimeType?: string;
  size?: number; // size in bytes
  progress?: number; // 0-100 for upload progress
  source?: 'upload' | 'paste' | 'drop';
  textPreview?: string;
}

interface AttachmentProps {
  attachment: AttachmentMeta;
  variant?: 'detailed' | 'pasted' | 'compact';
  onRemove?: (attachment: AttachmentMeta) => void;
}

export const formatFileSize = (bytes?: number): string => {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const getFileKind = (filename: string): string => {
  const ext = filename.split('.').pop()?.toUpperCase();
  return ext || 'FILE';
};

export const Attachment: React.FC<AttachmentProps> = ({
  attachment,
  variant,
  onRemove,
}) => {
  const { name, type, url, size, progress, mimeType, source, textPreview } = attachment;
  const isPastedVariant = variant === 'pasted' || source === 'paste';

  if (isPastedVariant) {
    return (
      <div className="attachment-tile-pasted" title={name}>
        <div className="pasted-text-preview">
          {textPreview || name}
        </div>
        <div className="pasted-bottom-row">
          <span className="pasted-badge">
            <IconClipboard size={12} style={{ color: '#475569' }} />
            PASTED
          </span>
          {onRemove && (
            <button
              type="button"
              className="attachment-remove-btn"
              onClick={() => onRemove(attachment)}
              title="Remove pasted snippet"
            >
              <IconX size={14} />
            </button>
          )}
        </div>
      </div>
    );
  }

  const isImage = type === 'image' || (mimeType && mimeType.startsWith('image/')) || (url && /\.(jpg|jpeg|png|webp|gif)$/i.test(name));
  const fileSizeStr = formatFileSize(size);
  const fileKind = getFileKind(name);

  return (
    <div className="attachment-tile" title={name}>
      {/* Left Thumbnail or Icon */}
      {isImage && url ? (
        <div className="attachment-thumb-container">
          <img src={url} alt={name} className="attachment-thumb-img" />
        </div>
      ) : (
        <div className="attachment-icon-badge">
          {fileKind === 'CSV' || fileKind === 'XLSX' ? (
            <IconDatabase size={18} style={{ color: '#7C3AED' }} />
          ) : isImage ? (
            <IconImage size={18} style={{ color: '#0284C7' }} />
          ) : (
            <IconFile size={18} style={{ color: '#475569' }} />
          )}
        </div>
      )}

      {/* Info Column */}
      <div className="attachment-info">
        <span className="attachment-name">{name}</span>
        <div className="attachment-meta-row">
          {fileSizeStr ? (
            <span>{fileSizeStr}</span>
          ) : (
            <span className="attachment-kind-badge">{fileKind}</span>
          )}
          {progress !== undefined && (
            <span style={{ color: '#0F172A', fontWeight: 600 }}>{progress}%</span>
          )}
        </div>
      </div>

      {/* Remove Button */}
      {onRemove && (
        <button
          type="button"
          className="attachment-remove-btn"
          onClick={() => onRemove(attachment)}
          title="Remove attachment"
        >
          <IconX size={14} />
        </button>
      )}

      {/* Upload Progress Bar */}
      {progress !== undefined && (
        <div className="attachment-progress-bar">
          <div
            className="attachment-progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
};

export interface AttachmentListProps {
  items: AttachmentMeta[];
  variant?: 'detailed' | 'pasted' | 'compact';
  onRemove?: (item: AttachmentMeta) => void;
}

export const AttachmentList: React.FC<AttachmentListProps> = ({
  items,
  variant = 'detailed',
  onRemove,
}) => {
  if (!items || items.length === 0) return null;

  return (
    <div className="attachment-list">
      {items.map((item, idx) => (
        <Attachment
          key={item.id || `${item.name}-${idx}`}
          variant={variant}
          attachment={item}
          onRemove={onRemove}
        />
      ))}
    </div>
  );
};

export default Attachment;
