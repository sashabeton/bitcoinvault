#include <policy/ddms.h>

#include <consensus/tx_verify.h>
#include <primitives/transaction.h>

const CScript WDMO_SCRIPT = CScript() << OP_HASH160 << std::vector<unsigned char>{11, 182, 127, 3, 232, 176, 211, 69, 45, 165, 222, 55, 211, 47, 198, 174, 240, 165, 160, 160} << OP_EQUAL; // TODO: replace with actual wdmo script; use ParseHex
MinerLicenses minerLicenses{};

void MinerLicenses::HandleTx(const CBaseTransaction& tx, const int height) {
	for (const auto& entry : ExtractLicenseEntries(tx, height)) {
		if (!FindLicense(entry))
			AddLicense(entry);
		else
			ModifyLicense(entry);
	}
}

std::vector<MinerLicenses::LicenseEntry> MinerLicenses::ExtractLicenseEntries(const CBaseTransaction& tx, const int height) {
	std::vector<MinerLicenses::LicenseEntry> entries;

	for (const auto& vout : tx.vout)
		if (IsLicenseTxHeader(vout.scriptPubKey))
			entries.push_back(ExtractLicenseEntry(vout.scriptPubKey, height));

	return entries;
}

/**
 * License TX consists of:
 * OP_RETURN - 1 byte
 * data size - 1 byte
 * size of license header - 1 byte
 * license header - 3 bytes by default
 * size of script - 1 byte
 * script - 20-32 bytes
 * hashrate in PH - 2 bytes
 */
MinerLicenses::LicenseEntry MinerLicenses::ExtractLicenseEntry(const CScript& scriptPubKey, const int height) {
	const int size = scriptPubKey.size();
	uint16_t hashRate = scriptPubKey[size - 2] << 8 | scriptPubKey[size - 1];
	std::string address = "";

	// TODO make it prettier
	for( int i = 7; i < 7 + scriptPubKey[6] /* size of script */; ++i)
		address += static_cast<char>(scriptPubKey[i]);

	return MinerLicenses::LicenseEntry{height, hashRate, address};
}

MinerLicenses::LicenseEntry* MinerLicenses::FindLicense(const MinerLicenses::LicenseEntry& entry) const {
	auto it = std::find_if(std::begin(licenses), std::end(licenses), [&entry](const MinerLicenses::LicenseEntry& license) {
		return license.address == entry.address;
	});

	return it != std::end(licenses) ? const_cast<MinerLicenses::LicenseEntry*>(&*it) : nullptr;
}

bool MinerLicenses::NeedToUpdateLicense(const MinerLicenses::LicenseEntry& entry) const {
	auto license = FindLicense(entry);
	return license != nullptr && license->height < entry.height;
}

void MinerLicenses::PushLicense(const int height, const uint16_t hashRate, const std::string& address) {
	auto it = std::find_if(std::begin(licenses), std::end(licenses), [&address](const MinerLicenses::LicenseEntry& obj) {
		return obj.address == address;
	});

	if (it == std::end(licenses))
		licenses.emplace_back(height, hashRate, address);
}

void MinerLicenses::AddLicense(const MinerLicenses::LicenseEntry& entry) {
	if (FindLicense(entry))
		return;

	licenses.emplace_back(entry.height, entry.hashRate, entry.address);
}

void MinerLicenses::ModifyLicense(const MinerLicenses::LicenseEntry& entry) {
	auto license = FindLicense(entry);
	if (!license || !NeedToUpdateLicense(entry))
		return;

	if (entry.hashRate == 0)
		licenses.erase(std::find(std::begin(licenses), std::end(licenses), *license));
	else
		license->hashRate = entry.hashRate;
}
