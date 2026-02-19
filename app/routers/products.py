from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.schemas import Product as ProductSchema, ProductCreate
from app.db_depends import get_db

# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=list[ProductSchema])
async def get_all_products(db: Session = Depends(get_db)):
    """
    Возвращает список всех товаров.
    """
    db_get_all_products = db.scalars(select(ProductModel).where(ProductModel.is_active == True)).all()
    return db_get_all_products


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Создаёт новый товар.
    """
    # Проверяем существование и активность категории
    category = db.scalars(select(CategoryModel).where(CategoryModel.id == product.category_id,
                                                      CategoryModel.is_active == True)).first()

    if category is None:
        raise HTTPException(status_code=400, detail='Category not found or inactive')

    # Создание нового продукта
    db_product = ProductModel(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(category_id: int, db: Session = Depends(get_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    # Проверяем существование и активность категории
    category_is_active = db.scalars(select(CategoryModel).where(CategoryModel.id == category_id,
                                                                CategoryModel.is_active == True)).first()

    if category_is_active is None:
        raise HTTPException(status_code=404, detail='Category not found or inactive')

    db_get_all_products_one_category = db.scalars(select(ProductModel).where(ProductModel.category_id == category_id))
    return db_get_all_products_one_category


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    # Проверяем существование и активность товара
    product_is_active = db.scalars(select(ProductModel).where(ProductModel.id == product_id,
                                                              ProductModel.is_active == True)).first()
    if product_is_active is None:
        raise HTTPException(status_code=404, detail='Product not found or inactive')

    # Проверяем существование и активность категории
    category_is_active = db.scalars(select(CategoryModel).where(
        CategoryModel.id == product_is_active.category_id)).first()

    if category_is_active is None:
        raise HTTPException(status_code=400, detail='Category not found or inactive')

    return product_is_active


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    """
    Обновляет товар по его ID.
    """
    # Проверяем существование и активность товара
    product_is_active = db.scalars(select(ProductModel).where(ProductModel.id == product_id,
                                                              ProductModel.is_active == True)).first()
    if product_is_active is None:
        raise HTTPException(status_code=404, detail='Product not found or inactive')

    # Проверяем существование и активность категории
    category_is_active = db.scalars(select(CategoryModel).where(
        CategoryModel.id == product_is_active.category_id)).first()

    if category_is_active is None:
        raise HTTPException(status_code=400, detail='Category not found or inactive')

    # Обновление товара
    db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product.model_dump())
    )
    db.commit()
    db.refresh(product_is_active)
    return product_is_active


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Удаляет товар по его ID.
    """
    # Проверяем существование и активность товара
    product_is_active = db.scalars(select(ProductModel).where(ProductModel.id == product_id,
                                                              ProductModel.is_active == True)).first()

    if product_is_active is None:
        raise HTTPException(status_code=404, detail='Product not found or inactive')

    db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id).values(is_active=False)
    )
    db.commit()

    return {"status": "success", "message": "Product marked as inactive"}
