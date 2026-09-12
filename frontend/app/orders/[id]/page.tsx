import { CustomerOrderDetailPage } from "../../../components/customer-pages";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <CustomerOrderDetailPage orderId={Number(id)} />;
}
