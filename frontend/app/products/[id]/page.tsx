import { ProductsPage } from "../../../components/customer-pages";

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ProductsPage productId={Number(id)} />;
}
