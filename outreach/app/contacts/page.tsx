import { Suspense } from "react";
import { ContactsScreen } from "@/components/ContactsScreen";

export default function ContactsPage() {
  return (
    <Suspense fallback={<p className="text-sm text-stone-500">Загрузка…</p>}>
      <ContactsScreen />
    </Suspense>
  );
}
