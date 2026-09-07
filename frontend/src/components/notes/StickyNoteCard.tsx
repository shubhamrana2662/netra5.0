import React, { useState } from 'react';
import type { CaseNote, StickyColor, NoteCategory } from '../../types/notes';
import s from './notes.module.css';

interface Props {
  note: CaseNote;
  onUpdate: (id: string, updates: Partial<CaseNote>) => void;
  onDelete: (id: string) => void;
  onTogglePin: (id: string) => void;
}

const COLOR_CLASSES: Record<StickyColor, string> = {
  amber: s.colorAmber,
  rose: s.colorRose,
  cyan: s.colorCyan,
  emerald: s.colorEmerald,
  purple: s.colorPurple,
  slate: s.colorSlate,
};

const SWATCH_COLORS: { color: StickyColor; hex: string }[] = [
  { color: 'amber', hex: '#F59E0B' },
  { color: 'rose', hex: '#F43F5E' },
  { color: 'cyan', hex: '#38BDF8' },
  { color: 'emerald', hex: '#10B981' },
  { color: 'purple', hex: '#A855F7' },
  { color: 'slate', hex: '#94A3B8' },
];

export function StickyNoteCard({ note, onUpdate, onDelete, onTogglePin }: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState(note.title);
  const [content, setContent] = useState(note.content);

  const handleBlur = () => {
    setIsEditing(false);
    if (title !== note.title || content !== note.content) {
      onUpdate(note.id, { title, content });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsEditing(false);
      setTitle(note.title);
      setContent(note.content);
    }
  };

  const colorClass = COLOR_CLASSES[note.color] || s.colorAmber;

  return (
    <div
      className={`${s.stickyCard} ${colorClass}`}
      style={{
        transform: `rotate(${note.rotation}deg)`,
      }}
    >
      {/* Pin button */}
      <button
        type="button"
        className={`${s.pinButton} ${note.isPinned ? s.pinned : ''}`}
        onClick={() => onTogglePin(note.id)}
        title={note.isPinned ? 'Unpin note' : 'Pin note to top'}
        aria-label={note.isPinned ? 'Unpin note' : 'Pin note to top'}
      >
        📌
      </button>

      {/* Top Metadata */}
      <div className={s.cardMetaTop}>
        <span className={s.categoryTag}>{note.category}</span>
        {note.type === 'formal' && (
          <span className={s.categoryTag} style={{ borderColor: 'rgba(255, 255, 255, 0.2)' }}>
            FORMAL LOG
          </span>
        )}
      </div>

      {/* Title */}
      {isEditing ? (
        <input
          type="text"
          className={s.inputField}
          style={{ width: '100%', marginBottom: 6, fontWeight: 600 }}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          autoFocus
        />
      ) : (
        <div
          className={s.cardTitle}
          onClick={() => setIsEditing(true)}
          title="Click to edit"
        >
          {note.title}
        </div>
      )}

      {/* Content */}
      {isEditing ? (
        <textarea
          className={s.textareaField}
          style={{ width: '100%', marginBottom: 8 }}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
        />
      ) : (
        <div
          className={s.cardContent}
          onClick={() => setIsEditing(true)}
          title="Click to edit"
        >
          {note.content || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Empty note... click to write</span>}
        </div>
      )}

      {/* Bottom Footer Controls */}
      <div className={s.cardBottom}>
        <div className={s.authorMeta}>
          <span>{note.author}</span>
          <span style={{ opacity: 0.7 }}>{note.updatedAt}</span>
        </div>

        <div className={s.cardActions}>
          {/* Color swatch picker */}
          <div className={s.swatchRow}>
            {SWATCH_COLORS.map((sw) => (
              <button
                key={sw.color}
                type="button"
                className={`${s.swatchDot} ${note.color === sw.color ? s.swatchDotActive : ''}`}
                style={{ background: sw.hex }}
                onClick={() => onUpdate(note.id, { color: sw.color })}
                title={`Set color: ${sw.color}`}
              />
            ))}
          </div>

          <button
            type="button"
            className={s.iconBtn}
            onClick={() => setIsEditing(!isEditing)}
            title="Edit note"
          >
            ✎
          </button>

          <button
            type="button"
            className={`${s.iconBtn} ${s.deleteBtn}`}
            onClick={() => onDelete(note.id)}
            title="Delete note"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
}
