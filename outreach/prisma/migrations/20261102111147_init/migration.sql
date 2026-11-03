-- CreateTable
CREATE TABLE "Contact" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "fullName" TEXT NOT NULL,
    "linkedinId" TEXT NOT NULL,
    "linkedinUrl" TEXT,
    "headline" TEXT,
    "occupation" TEXT NOT NULL,
    "company" TEXT,
    "industry" TEXT,
    "location" TEXT,
    "interests" TEXT NOT NULL DEFAULT '[]',
    "notes" TEXT,
    "status" TEXT NOT NULL DEFAULT 'NEW',
    "lastContactedAt" DATETIME,
    "searchText" TEXT NOT NULL DEFAULT '',
    "companyKey" TEXT NOT NULL DEFAULT '',
    "industryKey" TEXT NOT NULL DEFAULT '',
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "MessageDraft" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "contactId" TEXT NOT NULL,
    "goal" TEXT NOT NULL,
    "tone" TEXT NOT NULL,
    "language" TEXT NOT NULL DEFAULT 'ru',
    "generatedText" TEXT NOT NULL,
    "personalizationHooks" TEXT NOT NULL DEFAULT '[]',
    "risks" TEXT NOT NULL DEFAULT '[]',
    "suggestedFollowUp" TEXT NOT NULL DEFAULT '',
    "version" INTEGER NOT NULL,
    "isApproved" BOOLEAN NOT NULL DEFAULT false,
    "userFeedback" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "MessageDraft_contactId_fkey" FOREIGN KEY ("contactId") REFERENCES "Contact" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "UserProfile" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "currentRole" TEXT NOT NULL,
    "company" TEXT,
    "keyExperience" TEXT NOT NULL,
    "achievements" TEXT NOT NULL DEFAULT '[]',
    "valueProposition" TEXT NOT NULL,
    "preferredNextStep" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "Contact_linkedinId_key" ON "Contact"("linkedinId");

-- CreateIndex
CREATE INDEX "Contact_status_idx" ON "Contact"("status");

-- CreateIndex
CREATE INDEX "Contact_updatedAt_idx" ON "Contact"("updatedAt");

-- CreateIndex
CREATE INDEX "Contact_companyKey_idx" ON "Contact"("companyKey");

-- CreateIndex
CREATE INDEX "Contact_industryKey_idx" ON "Contact"("industryKey");

-- CreateIndex
CREATE INDEX "MessageDraft_contactId_idx" ON "MessageDraft"("contactId");
