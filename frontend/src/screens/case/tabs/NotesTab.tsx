import { CaseNotesSection } from "../../../components/notes/CaseNotesSection";
import type { Case } from "../../../data/types";

interface Props {
  caseId: string;
  caseData?: Case;
}

export function NotesTab({ caseId }: Props) {
  return (
    <div style={{ maxWidth: 1280, margin: "0 auto", paddingBottom: 60 }}>
      <CaseNotesSection caseId={caseId} isFullTab={true} />
    </div>
  );
}
