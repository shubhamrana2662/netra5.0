import React, { useState } from 'react';
import { useCaseNotes } from '../../state/useCaseNotes';
import { StickyNoteCard } from './StickyNoteCard';
import type { StickyColor, NoteCategory, NoteType } from '../../types/notes';
import s from './notes.module.css';

interface Props {
  caseId: string;
  isFullTab?: boolean;
}

const CATEGORIES: NoteCategory[] = [
  'HYPOTHESIS',
  'LEAD',
  'ACTION ITEM',
  'VERIFICATION',
  'EVIDENCE',
  'SUSPECT',
  'LEGAL / 65B',
];

const COLORS: { color: StickyColor; label: string; hex: string }[] = [
  { color: 'amber', label: 'Amber (Urgent/Lead)', hex: '#F59E0B' },
  { color: 'cyan', label: 'Cyan (Intelligence)', hex: '#38BDF8' },
  { color: 'rose', label: 'Rose (Critical/Threat)', hex: '#F43F5E' },
  { color: 'emerald', label: 'Emerald (Verified)', hex: '#10B981' },
  { color: 'purple', label: 'Purple (Analytical)', hex: '#A855F7' },
  { color: 'slate', label: 'Slate (Standard)', hex: '#94A3B8' },
];

export function CaseNotesSection({ caseId, isFullTab = false }: Props) {
  const { notes, addNote, updateNote, deleteNote, togglePin } = useCaseNotes(caseId);

  const [filter, setFilter] = useState<'all' | 'pinned' | 'sticky' | 'formal' | NoteCategory>('all');
  const [showNewBox, setShowNewBox] = useState(false);

  // New Note Form State
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newCategory, setNewCategory] = useState<NoteCategory>('LEAD');
  const [newColor, setNewColor] = useState<StickyColor>('amber');
  const [newType, setNewType] = useState<NoteType>('sticky');

  const handleCreateNote = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() && !newContent.trim()) return;

    addNote({
      title: newTitle.trim() || 'Untitled Note',
      content: newContent.trim(),
      category: newCategory,
      color: newColor,
      type: newType,
      isPinned: false,
    });

    // Reset form
    setNewTitle('');
    setNewContent('');
    setShowNewBox(false);
  };

  // Filter notes
  const filteredNotes = notes.filter((n) => {
    if (filter === 'all') return true;
    if (filter === 'pinned') return n.isPinned;
    if (filter === 'sticky') return n.type === 'sticky';
    if (filter === 'formal') return n.type === 'formal';
    return n.category === filter;
  });

  const pinnedCount = notes.filter((n) => n.isPinned).length;

  return (
    <section className={isFullTab ? '' : s.notesContainer} aria-label="Investigator Notes">
      {/* Header */}
      <div className={s.headerRow}>
        <div className={s.headerLeft}>
          <h3 className={s.title}>
            {isFullTab ? 'CASE NOTES & TACTICAL STICKY BOARD' : 'INVESTIGATOR NOTES & STICKY BOARD'}
          </h3>
          <span className={s.countBadge}>
            {pinnedCount > 0 ? `${pinnedCount} PINNED · ` : ''}
            {notes.length} {notes.length === 1 ? 'NOTE' : 'NOTES'}
          </span>
        </div>

        <div className={s.actions}>
          <button
            type="button"
            className={`${s.addBtn} ${s.addBtnPrimary}`}
            onClick={() => {
              setNewType('sticky');
              setShowNewBox(!showNewBox);
            }}
          >
            <span>+</span>
            <span>Add Sticky Note</span>
          </button>
          <button
            type="button"
            className={s.addBtn}
            onClick={() => {
              setNewType('formal');
              setShowNewBox(!showNewBox);
            }}
          >
            <span>+</span>
            <span>Add Formal Log</span>
          </button>
        </div>
      </div>

      {/* Filter Pills */}
      <div className={s.filterRow}>
        <button
          type="button"
          className={`${s.filterPill} ${filter === 'all' ? s.filterPillActive : ''}`}
          onClick={() => setFilter('all')}
        >
          All ({notes.length})
        </button>
        <button
          type="button"
          className={`${s.filterPill} ${filter === 'pinned' ? s.filterPillActive : ''}`}
          onClick={() => setFilter('pinned')}
        >
          📌 Pinned ({pinnedCount})
        </button>
        <button
          type="button"
          className={`${s.filterPill} ${filter === 'HYPOTHESIS' ? s.filterPillActive : ''}`}
          onClick={() => setFilter('HYPOTHESIS')}
        >
          Hypotheses
        </button>
        <button
          type="button"
          className={`${s.filterPill} ${filter === 'LEAD' ? s.filterPillActive : ''}`}
          onClick={() => setFilter('LEAD')}
        >
          Leads
        </button>
        <button
          type="button"
          className={`${s.filterPill} ${filter === 'ACTION ITEM' ? s.filterPillActive : ''}`}
          onClick={() => setFilter('ACTION ITEM')}
        >
          Action Items
        </button>
        <button
          type="button"
          className={`${s.filterPill} ${filter === 'VERIFICATION' ? s.filterPillActive : ''}`}
          onClick={() => setFilter('VERIFICATION')}
        >
          Verification
        </button>
      </div>

      {/* Inline New Note Box */}
      {showNewBox && (
        <div className={s.newNoteBox}>
          <form onSubmit={handleCreateNote} className={s.newNoteForm}>
            <div className={s.newNoteInputs}>
              <input
                type="text"
                className={s.inputField}
                placeholder="Note title or subject..."
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                style={{ flex: 2, minWidth: 200 }}
                autoFocus
              />
              <select
                className={s.inputField}
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as NoteCategory)}
                style={{ flex: 1, minWidth: 140 }}
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            <textarea
              className={s.textareaField}
              placeholder="Write investigative thoughts, hypotheses, witness statements, or pending verification tasks..."
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
            />

            <div className={s.newNoteFooter}>
              <div className={s.colorPickerGroup}>
                <span>Color:</span>
                <div className={s.swatchRow}>
                  {COLORS.map((c) => (
                    <button
                      key={c.color}
                      type="button"
                      className={`${s.swatchDot} ${newColor === c.color ? s.swatchDotActive : ''}`}
                      style={{ background: c.hex }}
                      onClick={() => setNewColor(c.color)}
                      title={c.label}
                    />
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  className={s.addBtn}
                  onClick={() => setShowNewBox(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={`${s.addBtn} ${s.addBtnPrimary}`}
                >
                  Pin to Case
                </button>
              </div>
            </div>
          </form>
        </div>
      )}

      {/* Sticky Board Grid */}
      {filteredNotes.length > 0 ? (
        <div className={s.stickyBoard}>
          {filteredNotes.map((note) => (
            <StickyNoteCard
              key={note.id}
              note={note}
              onUpdate={updateNote}
              onDelete={deleteNote}
              onTogglePin={togglePin}
            />
          ))}
        </div>
      ) : (
        <div className={s.emptyState}>
          No notes match the current filter. Click <b>+ Add Sticky Note</b> to pin an observation for this case.
        </div>
      )}
    </section>
  );
}
