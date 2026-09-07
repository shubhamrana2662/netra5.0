export type StickyColor = 'amber' | 'rose' | 'cyan' | 'emerald' | 'purple' | 'slate';

export type NoteType = 'sticky' | 'formal';

export type NoteCategory =
  | 'HYPOTHESIS'
  | 'LEAD'
  | 'EVIDENCE'
  | 'ACTION ITEM'
  | 'VERIFICATION'
  | 'SUSPECT'
  | 'LEGAL / 65B';

export interface CaseNote {
  id: string;
  caseId: string;
  title: string;
  content: string;
  type: NoteType;
  color: StickyColor;
  category: NoteCategory;
  isPinned: boolean;
  author: string;
  createdAt: string;
  updatedAt: string;
  rotation: number; // e.g. -2 to +2 degrees for tactile realistic feel
}
