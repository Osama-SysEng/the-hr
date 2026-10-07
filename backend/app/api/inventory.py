"""
The H.R - Inventory & Supply Chain API Routers
"""

from datetime import date, datetime, timezone
from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import (
    InventoryProduct, StockMovement, Supplier, PurchaseOrder, PurchaseOrderItem,
    Tenant, Employee
)
import uuid
import os
import shutil


router = APIRouter(prefix="/inventory", tags=["Inventory & Supply Chain"])


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


class ProductCreateRequest(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    barcode: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    unit: str = "piece"
    purchase_price: Optional[float] = None
    selling_price: Optional[float] = None
    current_stock: float = 0
    minimum_stock: float = 0
    maximum_stock: Optional[float] = None
    warehouse_location: Optional[str] = None


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    purchase_price: Optional[float] = None
    selling_price: Optional[float] = None
    current_stock: Optional[float] = None
    minimum_stock: Optional[float] = None
    maximum_stock: Optional[float] = None
    warehouse_location: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: str
    sku: str
    barcode: Optional[str] = None
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    unit: str
    purchase_price: Optional[float] = None
    selling_price: Optional[float] = None
    cost_method: str
    current_stock: float
    minimum_stock: float
    maximum_stock: Optional[float] = None
    warehouse_location: Optional[str] = None
    stock_status: str  # ok, low, out_of_stock, overstock
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StockMovementRequest(BaseModel):
    product_id: str
    movement_type: str  # in, out, transfer, adjustment
    quantity: float
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    cost_per_unit: Optional[float] = None
    notes: Optional[str] = None


class StockMovementResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    product_sku: str
    movement_type: str
    quantity: float
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    cost_per_unit: Optional[float] = None
    total_cost: Optional[float] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SupplierCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: str = "Net 30"
    notes: Optional[str] = None


class SupplierUpdateRequest(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None
    rating: Optional[float] = None
    on_time_delivery_rate: Optional[float] = None
    quality_rejection_rate: Optional[float] = None
    is_blacklisted: Optional[bool] = None
    notes: Optional[str] = None


class SupplierResponse(BaseModel):
    id: str
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: str
    rating: float
    on_time_delivery_rate: float
    quality_rejection_rate: float
    is_blacklisted: bool
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseOrderCreateRequest(BaseModel):
    supplier_id: Optional[str] = None
    request_date: date
    delivery_date: Optional[date] = None
    items: List[dict]  # [{product_id, description, quantity, unit_price}]
    notes: Optional[str] = None


class PurchaseOrderResponse(BaseModel):
    id: str
    po_number: str
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    status: str
    request_date: date
    delivery_date: Optional[date] = None
    items_count: int
    total_amount: float
    tax_amount: float
    grand_total: float
    notes: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PurchaseOrderDetailResponse(BaseModel):
    id: str
    po_number: str
    supplier: Optional[dict] = None
    status: str
    request_date: date
    delivery_date: Optional[date] = None
    items: List[dict]
    total_amount: float
    tax_amount: float
    grand_total: float
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    status_history: List[dict] = []
    notes: Optional[str] = None


class InventoryReportResponse(BaseModel):
    total_products: int
    total_skus: int
    total_value: float
    out_of_stock: int
    low_stock: int
    overstock: int
    products: List[ProductResponse]


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def _get_stock_status(product: InventoryProduct) -> str:
    if product.current_stock <= 0:
        return "out_of_stock"
    elif product.minimum_stock and product.current_stock <= product.minimum_stock:
        return "low"
    elif product.maximum_stock and product.current_stock >= product.maximum_stock:
        return "overstock"
    return "ok"


def _build_product_response(product: InventoryProduct) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        sku=product.sku,
        barcode=product.barcode,
        name=product.name,
        description=product.description,
        category=product.category,
        unit=product.unit,
        purchase_price=float(product.purchase_price) if product.purchase_price else None,
        selling_price=float(product.selling_price) if product.selling_price else None,
        cost_method=product.cost_method,
        current_stock=float(product.current_stock),
        minimum_stock=float(product.minimum_stock),
        maximum_stock=float(product.maximum_stock) if product.maximum_stock else None,
        warehouse_location=product.warehouse_location,
        stock_status=_get_stock_status(product),
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


# -----------------------------------------------------------------------------
# Products CRUD
# -----------------------------------------------------------------------------
@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    category: Optional[str] = Query(None),
    status: str = Query("all"),  # all, active, inactive, low_stock, out_of_stock
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """قائمة المنتجات"""
    tenant_id = current_user["tenant_id"]

    query = select(InventoryProduct).where(InventoryProduct.tenant_id == tenant_id)

    if category:
        query = query.where(InventoryProduct.category == category)

    if status == "active":
        query = query.where(InventoryProduct.is_active == True)
    elif status == "inactive":
        query = query.where(InventoryProduct.is_active == False)
    elif status == "low_stock":
        query = query.where(
            and_(
                InventoryProduct.current_stock > 0,
                InventoryProduct.current_stock <= InventoryProduct.minimum_stock,
            )
        )
    elif status == "out_of_stock":
        query = query.where(InventoryProduct.current_stock <= 0)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                InventoryProduct.name.ilike(search_term),
                InventoryProduct.sku.ilike(search_term),
                InventoryProduct.barcode.ilike(search_term),
            )
        )

    query = query.order_by(InventoryProduct.name)
    result = await db.execute(query)
    products = result.scalars().all()

    return [_build_product_response(p) for p in products]


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """الحصول على منتج محدد"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(InventoryProduct)
        .where(and_(InventoryProduct.id == product_id, InventoryProduct.tenant_id == tenant_id))
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المنتج غير موجود",
        )

    return _build_product_response(product)


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    request: ProductCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin")),
):
    """إنشاء منتج جديد"""
    tenant_id = current_user["tenant_id"]

    # Check for duplicate SKU
    result = await db.execute(
        select(InventoryProduct).where(
            and_(
                InventoryProduct.sku == request.sku,
                InventoryProduct.tenant_id == tenant_id,
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="رمز المنتج (SKU) مكرر",
        )

    product = InventoryProduct(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        **request.model_dump(),
        current_stock=Decimal(str(request.current_stock or 0)),
        minimum_stock=Decimal(str(request.minimum_stock or 0)),
        maximum_stock=Decimal(str(request.maximum_stock or 0)) if request.maximum_stock else None,
        purchase_price=Decimal(str(request.purchase_price or 0)),
        selling_price=Decimal(str(request.selling_price or 0)),
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    return _build_product_response(product)


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    request: ProductUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin")),
):
    """تحديث منتج"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(InventoryProduct).where(
            and_(InventoryProduct.id == product_id, InventoryProduct.tenant_id == tenant_id)
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المنتج غير موجود",
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ("current_stock", "minimum_stock", "maximum_stock", "purchase_price", "selling_price"):
            setattr(product, field, Decimal(str(value)) if value is not None else None)
        else:
            setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    return _build_product_response(product)


# -----------------------------------------------------------------------------
# Stock Movements
# -----------------------------------------------------------------------------
@router.post("/movements", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_movement(
    request: StockMovementRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """إضافة حركة مخزن"""
    tenant_id = current_user["tenant_id"]

    # Get product
    result = await db.execute(
        select(InventoryProduct).where(
            and_(InventoryProduct.id == request.product_id, InventoryProduct.tenant_id == tenant_id)
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المنتجغير موجود",
        )

    # Calculate total cost
    total_cost = Decimal(str(request.cost_per_unit or 0)) * Decimal(str(request.quantity))

    # Update stock
    if request.movement_type in ("in", "received"):
        product.current_stock += Decimal(str(request.quantity))
    elif request.movement_type in ("out", "issued"):
        if product.current_stock < Decimal(str(request.quantity)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"الكمية المتاحة للمنتج {product.name} هي {product.current_stock} فقط",
            )
        product.current_stock -= Decimal(str(request.quantity))
    elif request.movement_type == "adjustment":
        product.current_stock = Decimal(str(request.quantity))

    # Create movement record
    movement = StockMovement(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        product_id=request.product_id,
        movement_type=request.movement_type,
        quantity=Decimal(str(request.quantity)),
        reference_type=request.reference_type,
        reference_id=request.reference_id,
        from_location=request.from_location,
        to_location=request.to_location,
        cost_per_unit=Decimal(str(request.cost_per_unit or 0)),
        total_cost=total_cost,
        created_by=current_user.get("user_id"),
        notes=request.notes,
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)

    return StockMovementResponse(
        id=movement.id,
        product_id=movement.product_id,
        product_name=product.name,
        product_sku=product.sku,
        movement_type=movement.movement_type,
        quantity=float(movement.quantity),
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        from_location=movement.from_location,
        to_location=movement.to_location,
        cost_per_unit=float(movement.cost_per_unit or 0),
        total_cost=float(movement.total_cost or 0),
        created_by=movement.created_by,
        notes=movement.notes,
        created_at=movement.created_at,
    )


# -----------------------------------------------------------------------------
# Suppliers
# -----------------------------------------------------------------------------
@router.get("/suppliers", response_model=List[SupplierResponse])
async def list_suppliers(
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """قائمة الموردين"""
    tenant_id = current_user["tenant_id"]

    query = select(Supplier).where(Supplier.tenant_id == tenant_id)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Supplier.name.ilike(search_term),
                Supplier.email.ilike(search_term),
            )
        )

    query = query.order_by(Supplier.name)
    result = await db.execute(query)
    suppliers = result.scalars().all()

    return [SupplierResponse.model_validate(s) for s in suppliers]


@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    request: SupplierCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin")),
):
    """إنشاء مورد جديد"""
    tenant_id = current_user["tenant_id"]

    supplier = Supplier(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        **request.model_dump(),
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)

    return SupplierResponse.model_validate(supplier)


# -----------------------------------------------------------------------------
# Purchase Orders
# -----------------------------------------------------------------------------
@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    request: PurchaseOrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "company_admin")),
):
    """إنشاء أمر شراء جديد"""
    tenant_id = current_user["tenant_id"]

    # Generate PO number
    po_number = f"PO-{str(tenant_id).replace('-', '')[:6]}-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    # Calculate totals
    total_amount = Decimal("0")
    items_data = []
    for item in request.items:
        quantity = Decimal(str(item.get("quantity", 0)))
        unit_price = Decimal(str(item.get("unit_price", 0)))
        total = quantity * unit_price
        total_amount += total
        items_data.append({
            "product_id": item.get("product_id"),
            "description": item.get("description"),
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total,
            "received_quantity": Decimal("0"),
        })

    tax_amount = total_amount * Decimal("0.14")  # VAT assumed 14%
    grand_total = total_amount + tax_amount

    po = PurchaseOrder(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        po_number=po_number,
        supplier_id=request.supplier_id,
        status="draft",
        request_date=request.request_date,
        delivery_date=request.delivery_date,
        total_amount=total_amount,
        tax_amount=tax_amount,
        grand_total=grand_total,
        notes=request.notes,
        created_at=datetime.now(timezone.utc),
    )
    db.add(po)
    await db.flush()

    # Create items
    for item_data in items_data:
        item_data["po_id"] = po.id
        db.add(PurchaseOrderItem(**item_data))

    await db.commit()
    await db.refresh(po)

    # Load supplier name
    if po.supplier_id:
        supp_result = await db.execute(
            select(Supplier.name).where(Supplier.id == po.supplier_id)
        )
        supplier_name = supp_result.scalar()
    else:
        supplier_name = None

    return PurchaseOrderResponse(
        id=po.id,
        po_number=po.po_number,
        supplier_id=po.supplier_id,
        supplier_name=supplier_name,
        status=po.status,
        request_date=po.request_date,
        delivery_date=po.delivery_date,
        items_count=len(items_data),
        total_amount=float(po.total_amount),
        tax_amount=float(po.tax_amount),
        grand_total=float(po.grand_total),
        notes=po.notes,
        created_at=po.created_at,
    )


@router.get("/purchase-orders", response_model=List[PurchaseOrderResponse])
async def list_purchase_orders(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """قائمة أوامر الشراء"""
    tenant_id = current_user["tenant_id"]

    query = select(PurchaseOrder).where(PurchaseOrder.tenant_id == tenant_id)

    if status:
        query = query.where(PurchaseOrder.status == status)

    query = query.order_by(PurchaseOrder.created_at.desc())
    result = await db.execute(query)
    orders = result.scalars().all()

    response = []
    for order in orders:
        orders_items_result = await db.execute(
            select(func.count(PurchaseOrderItem.id)).where(
                PurchaseOrderItem.po_id == order.id
            )
        )
        items_count = orders_items_result.scalar() or 0

        supplier_result = await db.execute(
            select(Supplier.name).where(Supplier.id == order.supplier_id)
        )
        supplier_name = supplier_result.scalar()

        response.append(PurchaseOrderResponse(
            id=order.id,
            po_number=order.po_number,
            supplier_id=order.supplier_id,
            supplier_name=supplier_name,
            status=order.status,
            request_date=order.request_date,
            delivery_date=order.delivery_date,
            items_count=items_count,
            total_amount=float(order.total_amount),
            tax_amount=float(order.tax_amount),
            grand_total=float(order.grand_total),
            notes=order.notes,
            approved_by=order.approved_by,
            approved_at=order.approved_at,
            created_at=order.created_at,
            updated_at=order.updated_at,
        ))

    return response


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderDetailResponse)
async def get_purchase_order_detail(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """تفاصيل أمر شراء محدد"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(PurchaseOrder)
        .where(and_(PurchaseOrder.id == po_id, PurchaseOrder.tenant_id == tenant_id))
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product),
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="أمر الشراء غير موجود",
        )

    items_data = []
    for item in order.items:
        product_data = None
        if item.product:
            product_data = {
                "id": item.product.id,
                "name": item.product.name,
                "sku": item.product.sku,
                "current_stock": float(item.product.current_stock),
            }
        items_data.append({
            "id": item.id,
            "product_id": item.product_id,
            "product": product_data,
            "description": item.description,
            "quantity": float(item.quantity),
            "unit_price": float(item.unit_price),
            "total_price": float(item.total_price),
            "received_quantity": float(item.received_quantity),
        })

    supplier_data = None
    if order.supplier:
        supplier_data = SupplierResponse.model_validate(order.supplier)

    return PurchaseOrderDetailResponse(
        id=order.id,
        po_number=order.po_number,
        supplier=supplier_data,
        status=order.status,
        request_date=order.request_date,
        delivery_date=order.delivery_date,
        items=items_data,
        total_amount=float(order.total_amount),
        tax_amount=float(order.tax_amount),
        grand_total=float(order.grand_total),
        approved_by=order.approved_by,
        approved_at=order.approved_at,
        notes=order.notes,
        created_at=order.created_at,
    )


# -----------------------------------------------------------------------------
# Inventory Reports
# -----------------------------------------------------------------------------
@router.get("/report/summary", response_model=InventoryReportResponse)
async def inventory_summary_report(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """تقرير تلخيصي للمخزن"""
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(
            func.count(InventoryProduct.id).label("total_products"),
            func.count(InventoryProduct.sku).label("total_skus"),
            func.sum(InventoryProduct.current_stock * InventoryProduct.purchase_price).label("total_value"),
            func.sum(func.cast(
                and_(InventoryProduct.current_stock <= 0, InventoryProduct.is_active == True),
                Integer
            )).label("out_of_stock"),
            func.sum(func.cast(
                and_(
                    InventoryProduct.current_stock > 0,
                    InventoryProduct.current_stock <= InventoryProduct.minimum_stock,
                    InventoryProduct.is_active == True,
                ),
                Integer
            )).label("low_stock"),
            func.sum(func.cast(
                and_(
                    InventoryProduct.current_stock >= InventoryProduct.maximum_stock,
                    InventoryProduct.is_active == True,
                ),
                Integer
            )).label("overstock"),
        ).where(InventoryProduct.tenant_id == tenant_id)
    )
    stats = result.one()

    # Get all products
    prod_result = await db.execute(
        select(InventoryProduct).where(InventoryProduct.tenant_id == tenant_id)
    )
    products = prod_result.scalars().all()

    return InventoryReportResponse(
        total_products=stats.total_products or 0,
        total_skus=stats.total_skus or 0,
        total_value=round(float(stats.total_value or 0), 2),
        out_of_stock=stats.out_of_stock or 0,
        low_stock=stats.low_stock or 0,
        overstock=stats.overstock or 0,
        products=[_build_product_response(p) for p in products],
    )
