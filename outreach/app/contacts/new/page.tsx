"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ContactForm, emptyContactForm, type ContactFormValues } from "@/components/ContactForm";
import { apiJson, type ContactDto } from "@/lib/client";
import { linesToList } from "@/lib/text";

export default function NewContactPage() {
  const router = useRouter();
  const [values, setValues] = useState<ContactFormValues>(emptyContactForm);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function save() {
    setPending(true);
    setError("");
    try {
      const created = await apiJson<ContactDto>("/api/contacts", {
        method: "POST",
        body: JSON.stringify(payload(values)),
      });
      router.push(`/contacts/${created.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить контакт");
      setPending(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Новый контакт</h1>
        <p className="mt-1 text-sm text-stone-600">Достаточно имени, LinkedIn ID и рода занятий. Остальное можно добавить позже.</p>
      </div>
      <div className="card">
        <ContactForm values={values} onChange={setValues} onSubmit={() => void save()} submitLabel="Создать контакт" pending={pending} error={error} />
      </div>
    </div>
  );
}

function payload(values: ContactFormValues) {
  return {
    fullName: values.fullName,
    linkedinId: values.linkedinId,
    linkedinUrl: values.linkedinUrl,
    headline: values.headline,
    occupation: values.occupation,
    company: values.company,
    industry: values.industry,
    location: values.location,
    interests: linesToList(values.interestsText),
    notes: values.notes,
  };
}
