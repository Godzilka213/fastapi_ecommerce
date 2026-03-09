from app.auth import get_current_user

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.db_depends import get_async_db
from app.models.users import User as UserModel
from app.models.products import Product as ProductModel
from app.models.reviews import Review as ReviewModel
from app.schemas import Review as ReviewSchema, ReviewCreate

# Создаём маршрутизатор с префиксом и тегом
router = APIRouter(
    prefix="/reviews",
    tags=["reviews"]
)


async def update_product_rating(db: AsyncSession, product_id: int):
    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, product_id)
    product.rating = avg_rating
    await db.commit()


@router.get('/reviews', response_model=list[ReviewSchema])
async def get_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех активных отзывов.
    """
    db_reviews_stmt = await db.scalars(select(ReviewModel).where(ReviewModel.is_active == True))
    reviews = db_reviews_stmt.all()
    return reviews


@router.get('/products/{product_id}/reviews', response_model=list[ReviewSchema])
async def get_product_reviews(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех активных отзывов о товаре.
    """
    # Проверяем существование и активность отзывов
    db_reviews_stmt = await db.scalars(select(ReviewModel).where(ReviewModel.product_id == product_id,
                                                                 ReviewModel.is_active == True))
    db_reviews = db_reviews_stmt.all()
    if not db_reviews:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Reviews not found or inactive')
    # Проверяем существование и активность товара
    db_review = await db.scalar(select(ProductModel).where(ProductModel.id == product_id,
                                                           ProductModel.is_active == True))
    if not db_review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Product not found or inactive')

    return db_reviews


@router.post('/reviews', response_model=ReviewSchema)
async def create_review(
        review: ReviewCreate,
        db: AsyncSession = Depends(get_async_db),
        user: UserModel = Depends(get_current_user)
):
    """
    Создает новый отзыв (только для 'buyer')
    """
    # Проверяем роль пользователя
    if user.role != 'buyer':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not allowed to perform this action')
    # Проверяем существование и активность товара
    db_product = await db.scalar(select(ProductModel).where(ProductModel.id == review.product_id,
                                                            ProductModel.is_active == True))
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found')
    if 1 < review.grade < 5:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Grade must be between 1 and 5')

    db_add_review = ReviewModel(**review.model_dump(), user_id=user.id)
    db.add(db_add_review)
    await db.commit()
    await db.refresh(db_add_review)  # Для получения id и is_active из базы
    await update_product_rating(db, product_id=review.product_id)
    return db_add_review


@router.delete('/reviews/{review_id}', response_model=ReviewSchema)
async def delete_review(
        review_id: int,
        db: AsyncSession = Depends(get_async_db),
        user: UserModel = Depends(get_current_user)
):
    """
    Выполняет мягкое удаление отзыва,
    если он принадлежит текущему покупателю или администратору (только для 'buyer' и 'admin').
    """
    # Проверяем наличие отзыва у пользователя и его активность
    db_user_review = await db.scalar(select(UserModel).where(ReviewModel.user_id == user.id,
                                                             UserModel.is_active == True))
    if not db_user_review or user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to perform this action")
    # Проверяем существование и активность отзыва
    db_review_model = await db.scalar(select(ReviewModel).where(ReviewModel.id == review_id,
                                                                ReviewModel.user_id == user.id,
                                                                ReviewModel.is_active == True))
    if not db_review_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Review not found or inactive')

    db_review_model.is_active = False
    await db.commit()
    await db.refresh(db_review_model)  # Для возврата is_active = False
    await update_product_rating(db, product_id=db_review_model.product_id)
    return {'message': 'Review deleted'}
