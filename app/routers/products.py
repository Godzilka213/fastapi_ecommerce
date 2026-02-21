from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update

from sqlalchemy.ext.asyncio import AsyncSession
from app.db_depends import get_async_db

from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.schemas import Product as ProductSchema, ProductCreate

# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=list[ProductSchema])
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    db_products_stmt = await db.scalars(select(ProductModel).where(ProductModel.is_active == True))
    db_products = db_products_stmt.all()
    return db_products


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Создаёт новый товар.
    """
    # Проверяем существование и активность категории
    db_category_stmt = await db.scalars(select(CategoryModel).where(CategoryModel.id == product.category_id,
                                                                    CategoryModel.is_active == True))
    db_category = db_category_stmt.first()
    if not db_category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Category not found or inactive')

    # Создание нового продукта
    db_product = ProductModel(**product.model_dump())
    db.add(db_product)
    await db.commit()
    return db_product


@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    # Проверяем существование и активность категории
    db_category_stmt = await db.scalars(select(CategoryModel).where(CategoryModel.id == category_id,
                                                                    CategoryModel.is_active == True))
    db_category = db_category_stmt.first()
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found or inactive')

    db_get_all_products_one_category_stmt = await db.scalars(
        select(ProductModel).where(ProductModel.category_id == category_id,
                                   ProductModel.is_active == True))
    db_get_all_products_one_category = db_get_all_products_one_category_stmt.all()
    return db_get_all_products_one_category


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    # Проверяем существование и активность товара
    db_product_stmt = await db.scalars(select(ProductModel).where(ProductModel.id == product_id,
                                                                  ProductModel.is_active == True))
    db_product = db_product_stmt.first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found or inactive')

    # Проверяем существование и активность категории
    db_category_stmt = await db.scalars(select(CategoryModel).where(
        CategoryModel.id == db_product.category_id,
        CategoryModel.is_active == True))
    db_category = db_category_stmt.first()
    if not db_category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Category not found or inactive')

    return db_product


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(product_id: int, product: ProductCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Обновляет товар по его ID.
    """
    # Проверяем существование и активность товара
    db_product_stmt = await db.scalars(select(ProductModel).where(ProductModel.id == product_id,
                                                                  ProductModel.is_active == True))
    db_product = db_product_stmt.first()
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found or inactive')

    # Проверяем существование и активность категории
    db_category_stmt = await db.scalars(select(CategoryModel).where(
        CategoryModel.id == db_product.category_id,
        CategoryModel.is_active == True))
    db_category = db_category_stmt.first()
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Category not found or inactive')

    # Обновление товара
    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product.model_dump())
    )
    await db.commit()
    return db_product


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Удаляет товар по его ID.
    """
    # Проверяем существование и активность товара
    db_product_stmt = await db.scalars(select(ProductModel).where(ProductModel.id == product_id,
                                                                  ProductModel.is_active == True))
    db_product = db_product_stmt.first()

    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found or inactive')

    # Изменяем объект установив is_active=False и сохраняем
    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(is_active=False)
    )
    await db.commit()
    return {"status": "success", "message": "Product marked as inactive"}
