import { useState, useEffect, useCallback } from 'react';
import type { CaseNote, StickyColor, NoteCategory } from '../types/notes';

const STORAGE_PREFIX = 'cd_case_notes_v1_';

const DEFAULT_SEEDS: Record<string, CaseNote[]> = {
  'CYB-2026-042': [
    {
      id: 'note-42-1',
      caseId: 'CYB-2026-042',
      title: 'Device A83F-29 IMEI Corroboration',
      content: 'IMEI 86294005•••• needs cell tower co-location verification. Tower jump at 09:42 indicates movement towards Salt Lake Sector V.',
      type: 'sticky',
      color: 'amber',
      category: 'LEAD',
      isPinned: true,
      author: 'IO Sharma · Cyber Cell',
      createdAt: '25m ago',
      updatedAt: '25m ago',
      rotation: -1.2,
    },
    {
      id: 'note-42-2',
      caseId: 'CYB-2026-042',
      title: 'Axis Bank Subpoena (Sec 91 CrPC)',
      content: 'Notice served to Branch Manager for Account ••4821. Requesting beneficiary KYC, mandate holder photos, and ATM egress footage from 09:56.',
      type: 'sticky',
      color: 'rose',
      category: 'ACTION ITEM',
      isPinned: true,
      author: 'Insp. Mukherjee',
      createdAt: '1h ago',
      updatedAt: '45m ago',
      rotation: 1.5,
    },
    {
      id: 'note-42-3',
      caseId: 'CYB-2026-042',
      title: 'Hypothesis: Rajesh Kumar Mule Intermediary',
      content: 'Inferred link between Rajesh Kumar and Account #72 suggests proxy mule intermediary rather than direct operator. Check UPI device fingerprint concurrency.',
      type: 'sticky',
      color: 'cyan',
      category: 'HYPOTHESIS',
      isPinned: false,
      author: 'Analyst Roy',
      createdAt: '2h ago',
      updatedAt: '2h ago',
      rotation: -0.8,
    },
    {
      id: 'note-42-4',
      caseId: 'CYB-2026-042',
      title: 'Section 65B Certificate Generated',
      content: 'Cryptographic hash SHA-256 (a8f9b2...32c1) locked for WhatsApp extraction archive and forensic disk image.',
      type: 'formal',
      color: 'emerald',
      category: 'LEGAL / 65B',
      isPinned: false,
      author: 'Forensics Lead Patel',
      createdAt: 'Yesterday',
      updatedAt: 'Yesterday',
      rotation: 0.5,
    },
  ],
  'CYB-2026-018': [
    {
      id: 'note-18-1',
      caseId: 'CYB-2026-018',
      title: 'Regional Cluster 2 Hawala Pattern',
      content: 'Cross-border remittance micro-layering observed. Match transaction timestamps against Telegram broadcast channel.',
      type: 'sticky',
      color: 'amber',
      category: 'LEAD',
      isPinned: true,
      author: 'IO Sen',
      createdAt: '3h ago',
      updatedAt: '3h ago',
      rotation: 1.2,
    },
    {
      id: 'note-18-2',
      caseId: 'CYB-2026-018',
      title: 'Awaiting FIU-IND STR Ingestion',
      content: 'Suspicious Transaction Reports requested for 4 shell entities registered in Jaipur jurisdiction.',
      type: 'sticky',
      color: 'cyan',
      category: 'ACTION ITEM',
      isPinned: false,
      author: 'IO Sen',
      createdAt: '5h ago',
      updatedAt: '5h ago',
      rotation: -1.0,
    },
  ],
  'CYB-2026-041': [
    {
      id: 'note-41-1',
      caseId: 'CYB-2026-041',
      title: 'Phishing Upstream Nameserver Pivot',
      content: 'Registrant identity obscured by privacy proxy. Trace upstream nameserver IP co-tenancy and passive DNS resolutions.',
      type: 'sticky',
      color: 'rose',
      category: 'HYPOTHESIS',
      isPinned: true,
      author: 'CERT-In Liaison',
      createdAt: 'Yesterday',
      updatedAt: 'Yesterday',
      rotation: -1.4,
    },
  ],
};

export function useCaseNotes(caseId: string) {
  const storageKey = `${STORAGE_PREFIX}${caseId}`;

  const loadInitialNotes = (): CaseNote[] => {
    if (typeof window === 'undefined') return [];
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Failed to load notes from localStorage', e);
    }
    // Return default seed or initial starter
    return DEFAULT_SEEDS[caseId] || [
      {
        id: `note-${caseId}-init`,
        caseId,
        title: 'Initial Case Observation',
        content: 'Case opened for investigation. Record preliminary findings, leads, or suspect coordinates here.',
        type: 'sticky',
        color: 'amber',
        category: 'LEAD',
        isPinned: true,
        author: 'Investigator',
        createdAt: 'Just now',
        updatedAt: 'Just now',
        rotation: 0.8,
      },
    ];
  };

  const [notes, setNotes] = useState<CaseNote[]>(loadInitialNotes);

  // Sync when caseId changes
  useEffect(() => {
    setNotes(loadInitialNotes());
  }, [caseId]);

  // Persist whenever notes change
  const saveNotes = useCallback((newNotes: CaseNote[]) => {
    setNotes(newNotes);
    try {
      localStorage.setItem(storageKey, JSON.stringify(newNotes));
    } catch (e) {
      console.warn('Failed to save notes to localStorage', e);
    }
  }, [storageKey]);

  const addNote = useCallback((partial: Partial<CaseNote>): CaseNote => {
    const randomRotation = Number(((Math.random() * 3) - 1.5).toFixed(1));
    const newNote: CaseNote = {
      id: `note-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
      caseId,
      title: partial.title || 'New Observation',
      content: partial.content || '',
      type: partial.type || 'sticky',
      color: partial.color || 'amber',
      category: partial.category || 'LEAD',
      isPinned: partial.isPinned || false,
      author: partial.author || 'Investigator',
      createdAt: 'Just now',
      updatedAt: 'Just now',
      rotation: randomRotation,
    };

    const updated = [newNote, ...notes];
    saveNotes(updated);
    return newNote;
  }, [caseId, notes, saveNotes]);

  const updateNote = useCallback((id: string, updates: Partial<CaseNote>) => {
    const updated = notes.map(n => {
      if (n.id === id) {
        return {
          ...n,
          ...updates,
          updatedAt: 'Just now',
        };
      }
      return n;
    });
    saveNotes(updated);
  }, [notes, saveNotes]);

  const deleteNote = useCallback((id: string) => {
    const updated = notes.filter(n => n.id !== id);
    saveNotes(updated);
  }, [notes, saveNotes]);

  const togglePin = useCallback((id: string) => {
    const updated = notes.map(n => {
      if (n.id === id) {
        return {
          ...n,
          isPinned: !n.isPinned,
          updatedAt: 'Just now',
        };
      }
      return n;
    });
    saveNotes(updated);
  }, [notes, saveNotes]);

  const setColor = useCallback((id: string, color: StickyColor) => {
    updateNote(id, { color });
  }, [updateNote]);

  // Sort notes: pinned first, then by creation
  const sortedNotes = [...notes].sort((a, b) => {
    if (a.isPinned && !b.isPinned) return -1;
    if (!a.isPinned && b.isPinned) return 1;
    return 0;
  });

  return {
    notes: sortedNotes,
    rawNotes: notes,
    addNote,
    updateNote,
    deleteNote,
    togglePin,
    setColor,
  };
}
