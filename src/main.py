from fastapi import FastAPI
from routes import base, data, nlp
from helpers.config import get_settings
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.llm.providers.template_parser import TemplateParser
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

# Import metrics setup
from utils.metrics import setup_metrics

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Retrieve settings
    settings = get_settings()

    # Setup PostgreSQL connection
    postgres_conn = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    db_engine = create_async_engine(postgres_conn)
    db_client = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    # Setup LLM and Vector DB factories
    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(config=settings, db_client=db_client)

    # Attach shared resources to app.state
    app.state.db_engine = db_engine
    app.state.db_client = db_client
    app.state.generation_client = llm_provider_factory.create(provider=settings.GENERATION_BACKEND)
    app.state.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)
    app.state.embedding_client = llm_provider_factory.create(provider=settings.EMBEDDING_BACKEND)
    app.state.embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID,
                                                   embedding_size=settings.EMBEDDING_MODEL_SIZE)
    app.state.vectordb_client = vectordb_provider_factory.create(provider=settings.VECTOR_DB_BACKEND)
    await app.state.vectordb_client.connect()
    app.state.template_parser = TemplateParser(language=settings.PRIMARY_LANG,
                                               default_language=settings.DEFAULT_LANG)

    # Initialize metricsы
    setup_metrics(app)

    print("Resources initialized successfully!")
    yield  # The application runs here

    # Cleanup resources during shutdown
    db_engine.dispose()
    await app.state.vectordb_client.disconnect()
    print("Resources cleaned up successfully!")

# Create the FastAPI application with the lifespan
app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
