from alembic import op
import sqlalchemy as sa
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None
copy_status_enum = sa.Enum('available', 'issued', 'lost', name='copystatus')

def upgrade():
    op.create_table('authors', sa.Column('id', sa.Integer, primary_key=True), sa.Column('full_name', sa.String(255), nullable=False), sa.Column('bio', sa.Text, nullable=True))
    op.create_table('faculties', sa.Column('id', sa.Integer, primary_key=True), sa.Column('name', sa.String(255), nullable=False, unique=True))
    op.create_table('branches', sa.Column('id', sa.Integer, primary_key=True), sa.Column('name', sa.String(255), nullable=False, unique=True), sa.Column('address', sa.String(255), nullable=True))
    op.create_table('books', sa.Column('id', sa.Integer, primary_key=True), sa.Column('title', sa.String(255), nullable=False), sa.Column('isbn', sa.String(20), nullable=True, unique=True), sa.Column('published_year', sa.Integer, nullable=True), sa.Column('author_id', sa.Integer, sa.ForeignKey('authors.id'), nullable=False), sa.Column('faculty_id', sa.Integer, sa.ForeignKey('faculties.id'), nullable=True))
    op.create_table('copies', sa.Column('id', sa.Integer, primary_key=True), sa.Column('inventory_number', sa.String(50), nullable=False), sa.Column('status', copy_status_enum, nullable=False, server_default='available'), sa.Column('book_id', sa.Integer, sa.ForeignKey('books.id'), nullable=False), sa.Column('branch_id', sa.Integer, sa.ForeignKey('branches.id'), nullable=False), sa.UniqueConstraint('inventory_number', name='uq_copy_inventory_number'))
    op.create_table('loans', sa.Column('id', sa.Integer, primary_key=True), sa.Column('copy_id', sa.Integer, sa.ForeignKey('copies.id'), nullable=False), sa.Column('borrower_name', sa.String(255), nullable=False), sa.Column('issued_at', sa.DateTime, nullable=False), sa.Column('returned_at', sa.DateTime, nullable=True))

def downgrade():
    op.drop_table('loans')
    op.drop_table('copies')
    op.drop_table('books')
    op.drop_table('branches')
    op.drop_table('faculties')
    op.drop_table('authors')
    copy_status_enum.drop(op.get_bind(), checkfirst=True)