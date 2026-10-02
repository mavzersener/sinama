/**
 * Vitest Test Setup
 */
import { vi, afterAll, beforeEach } from "vitest";

// Global test configuration
process.env.NODE_ENV = "test";

// Clean console noise during tests (uncomment to enable)
// vi.spyOn(console, "log").mockImplementation(() => {});
// vi.spyOn(console, "warn").mockImplementation(() => {});
// vi.spyOn(console, "error").mockImplementation(() => {});

// Mock environment variables
// .env'de HARP tanımlı olsa bile testler canlı HARP'a makbuz İLETMEZ
// (dotenv var olan anahtarı ezmez). HARP testleri env'i kendisi kurar.
vi.stubEnv("HARP_SERVICE_URL", "");
vi.stubEnv("HARP_TOKEN", "");

// Before each test: reset state
beforeEach(() => {
  // Any global per-test cleanup
});

// After all tests: cleanup
afterAll(() => {
  vi.restoreAllMocks();
});
