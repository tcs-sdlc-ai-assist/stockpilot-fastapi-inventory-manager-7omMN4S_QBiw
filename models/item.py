from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    category: Mapped["Category"] = relationship("Category", back_populates="items", lazy="selectin")
    creator: Mapped["User"] = relationship("User", back_populates="inventory_items", lazy="selectin")

    @property
    def total_value(self) -> float:
        return self.quantity * self.unit_price

    @property
    def is_low_stock(self) -> bool:
        return 0 < self.quantity <= self.reorder_level

    @property
    def is_out_of_stock(self) -> bool:
        return self.quantity == 0

    @property
    def low_stock_threshold(self) -> int:
        return self.reorder_level

    def __repr__(self) -> str:
        return f"<InventoryItem(id={self.id}, name='{self.name}', sku='{self.sku}', quantity={self.quantity})>"