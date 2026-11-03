import { ContactScreen } from "@/components/ContactScreen";

export default async function ContactPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ContactScreen id={id} />;
}
