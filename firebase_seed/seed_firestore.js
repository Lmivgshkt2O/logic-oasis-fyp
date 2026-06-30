const fs = require("node:fs");
const path = require("node:path");
const admin = require("firebase-admin");

const seedPath = path.join(__dirname, "seed_data.json");
const credentialCandidates = [
  path.join(__dirname, "serviceAccountKey.json"),
  path.join(__dirname, "serviceAccountKey.json.json"),
];

function findCredentialPath() {
  return credentialCandidates.find((candidate) => fs.existsSync(candidate));
}

function convertSpecialValues(value) {
  if (value === "__SERVER_TIMESTAMP__") {
    return admin.firestore.FieldValue.serverTimestamp();
  }

  if (Array.isArray(value)) {
    return value.map(convertSpecialValues);
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, nestedValue]) => [
        key,
        convertSpecialValues(nestedValue),
      ]),
    );
  }

  return value;
}

async function seedCollection(db, collectionName, documents) {
  const entries = Object.entries(documents);
  if (entries.length === 0) return;

  let batch = db.batch();
  let writes = 0;
  let total = 0;

  for (const [documentId, documentData] of entries) {
    const ref = db.collection(collectionName).doc(documentId);
    batch.set(ref, convertSpecialValues(documentData), { merge: true });
    writes += 1;
    total += 1;

    if (writes === 450) {
      await batch.commit();
      batch = db.batch();
      writes = 0;
    }
  }

  if (writes > 0) {
    await batch.commit();
  }

  console.log(`Seeded ${total} document(s) into ${collectionName}`);
}

async function main() {
  const credentialPath = findCredentialPath();
  if (!credentialPath) {
    throw new Error(
      "Missing Firebase service account. Place serviceAccountKey.json in firebase_seed.",
    );
  }

  if (!fs.existsSync(seedPath)) {
    throw new Error(`Missing seed data file: ${seedPath}`);
  }

  const serviceAccount = require(credentialPath);
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
  });

  const db = admin.firestore();
  const seedData = JSON.parse(fs.readFileSync(seedPath, "utf8"));

  for (const [collectionName, documents] of Object.entries(seedData)) {
    await seedCollection(db, collectionName, documents);
  }

  console.log("Logic Oasis FYP1 Firestore demo seed completed.");
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
