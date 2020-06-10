#include <validation.h>
#include <consensus/tx_verify.h>
#include <consensus/validation.h>
#include <index/txindex.h>
#include <script/script.h>
#include <test/test_bitcoin.h>
#include <util/memory.h>

#include <memory>

#include <boost/test/unit_test.hpp>

static CMutableTransaction createCoinbase() {
	CMutableTransaction coinbaseTx;

	coinbaseTx.nVersion = 1;
	coinbaseTx.vin.resize(1);
	coinbaseTx.vout.resize(1);
	coinbaseTx.vin[0].scriptSig = CScript() << OP_11 << OP_EQUAL;
	coinbaseTx.vin[0].prevout.SetNull();
	coinbaseTx.vout[0].nValue = 50000;
	coinbaseTx.vout[0].scriptPubKey = WDMO_SCRIPT;

	return coinbaseTx;
}

static CMutableTransaction createLicenseTransaction(const uint256 parentHash) {
	CMutableTransaction tx;
	tx.vin.resize(1);
	tx.vin[0].scriptSig = CScript() << OP_11;
	tx.vin[0].prevout.hash = parentHash;
	tx.vin[0].prevout.n = 0;
	tx.vout.resize(2);
	tx.vout[0].scriptPubKey = CScript();
	tx.vout[0].nValue = 49000;
	tx.vout[1].scriptPubKey = CScript() << OP_RETURN << std::vector<unsigned char>{3, 76, 84, 120, 20, 169, 20, 230, 53, 247, 106, 15, 189, 177, 112, 86, 88, 161, 227, 176, 86, 115, 120, 7, 74, 0, 5};
	tx.vout[1].nValue = 0;

	return tx;
}

struct DdmsSetup : public TestChain100Setup {
	DdmsSetup()
		: TestChain100Setup() {
		minerLicenses = MinerLicenses{};
	}
	~DdmsSetup() = default;
};

BOOST_FIXTURE_TEST_SUITE(ddms_tests, DdmsSetup)

BOOST_AUTO_TEST_CASE(shouldIsLicenseTxHeaderReturnTrueWhenProcessingLTxScriptPubKey)
{
	CScript ltxScriptPubKey = CScript() << OP_RETURN << std::vector<unsigned char>{3, 76, 84, 120, 20, 169, 20, 230, 53, 247, 106, 15, 189, 177, 112, 86, 88, 161, 227, 176, 86, 115, 120, 7, 74, 0, 5};
	BOOST_CHECK(IsLicenseTxHeader(ltxScriptPubKey));
}

BOOST_AUTO_TEST_CASE(shouldIsLicenseTxHeaderReturnFalseWhenNotProcessingLTxScriptPubKey)
{
	CScript notLtxScriptPubKey = CScript() << OP_RETURN << std::vector<unsigned char>{2, 31, 72, 20, 169, 20, 230, 53, 247, 106, 15, 189, 177, 112, 86, 88, 161, 227, 176, 86, 115, 120, 7, 74, 0, 5};
	BOOST_CHECK(!IsLicenseTxHeader(notLtxScriptPubKey));
}

BOOST_AUTO_TEST_CASE(shouldIsLicenseTxReturnFalseWhenTxNullOrCoinbase)
{
	CMutableTransaction coinbaseTx, nullTx;
	coinbaseTx = createCoinbase();

	BOOST_CHECK(!IsLicenseTx(CTransaction(nullTx)));
	BOOST_CHECK(!IsLicenseTx(CTransaction(coinbaseTx)));
}

BOOST_AUTO_TEST_CASE(shouldIsLicenseTxReturnFalseWhenTxWasNotSentByWDMO)
{
	g_txindex = MakeUnique<TxIndex>(1 << 20, true);
	g_txindex->Start();

	CScript fakeWdmoScript = WDMO_SCRIPT; --fakeWdmoScript[1];
	auto blk = CreateAndProcessBlock({}, fakeWdmoScript);
	CMutableTransaction lTx = createLicenseTransaction(blk.vtx[0]->GetHash());

	CreateAndProcessBlock({lTx}, WDMO_SCRIPT);

	// Allow tx index to catch up with the block index.
	constexpr int64_t timeout_ms = 10 * 1000;
	int64_t time_start = GetTimeMillis();
	while (!g_txindex->BlockUntilSyncedToCurrentChain()) {
		BOOST_REQUIRE(time_start + timeout_ms > GetTimeMillis());
		MilliSleep(100);
	}

	BOOST_CHECK(g_txindex->BlockUntilSyncedToCurrentChain());
	BOOST_CHECK(!IsLicenseTx(CTransaction(lTx)));

	g_txindex->Stop();
	g_txindex.reset();
}

BOOST_AUTO_TEST_CASE(shouldIsLicenseTxReturnFalseWhenSentByWDMOButNoLTxHeaderFound)
{
	auto blk = CreateAndProcessBlock({}, WDMO_SCRIPT);
	CMutableTransaction lTx = createLicenseTransaction(blk.vtx[0]->GetHash());
	lTx.vout[0].scriptPubKey = WDMO_SCRIPT;
	lTx.vout[1].scriptPubKey = CScript();

	CreateAndProcessBlock({lTx}, WDMO_SCRIPT);

	BOOST_CHECK(!IsLicenseTx(CTransaction(lTx)));
}

BOOST_AUTO_TEST_CASE(shouldIsLicenseTxReturnTrueIfLTxHeaderFoundAndSentByWDMOCheckedInTxIndex)
{
	g_txindex = MakeUnique<TxIndex>(1 << 20, true);
	g_txindex->Start();

	auto blk = CreateAndProcessBlock({}, WDMO_SCRIPT);
	CMutableTransaction lTx = createLicenseTransaction(blk.vtx[0]->GetHash());
	lTx.vout[0].scriptPubKey = WDMO_SCRIPT;
	CreateAndProcessBlock({lTx}, WDMO_SCRIPT);

	// Allow tx index to catch up with the block index.
	constexpr int64_t timeout_ms = 10 * 1000;
	int64_t time_start = GetTimeMillis();
	while (!g_txindex->BlockUntilSyncedToCurrentChain()) {
		BOOST_REQUIRE(time_start + timeout_ms > GetTimeMillis());
		MilliSleep(100);
	}

    BOOST_CHECK(g_txindex->BlockUntilSyncedToCurrentChain());
	BOOST_CHECK(IsLicenseTx(CTransaction(lTx)));

	g_txindex->Stop();
	g_txindex.reset();
}

BOOST_AUTO_TEST_CASE(shouldIsLicenseTxReturnTrueIfLTxHeaderFoundAndSentByWDMOCheckedInCoinsCacheView)
{
	auto blk = CreateAndProcessBlock({}, WDMO_SCRIPT);
	CMutableTransaction lTx = createLicenseTransaction(blk.vtx[0]->GetHash());
	lTx.vout[0].scriptPubKey = WDMO_SCRIPT;
	CreateAndProcessBlock({lTx}, WDMO_SCRIPT);

	BOOST_CHECK(IsLicenseTx(CTransaction(lTx)));
}

BOOST_AUTO_TEST_CASE(shouldAddLicenseIfCorrectLtxProvided)
{
	auto coinbaseTx = createCoinbase();
	auto lTx = createLicenseTransaction(coinbaseTx.GetHash());

	minerLicenses.HandleTx(CTransaction(lTx), 1);
	BOOST_CHECK_EQUAL(1, minerLicenses.GetLicenses().size());

	lTx.vout[1].scriptPubKey[7]++; // other miner's address
	minerLicenses.HandleTx(CTransaction(lTx), 2);
	BOOST_CHECK_EQUAL(2, minerLicenses.GetLicenses().size());
}

BOOST_AUTO_TEST_CASE(shouldNotAddLicenseIfAlreadyExists)
{
	auto coinbaseTx = createCoinbase();
	auto lTx = createLicenseTransaction(coinbaseTx.GetHash());

	minerLicenses.HandleTx(CTransaction(lTx), 1);
	minerLicenses.HandleTx(CTransaction(lTx), 2);
	BOOST_CHECK_EQUAL(1, minerLicenses.GetLicenses().size());
}

BOOST_AUTO_TEST_CASE(shouldOnlyModifyLicenseIfAlreadyPushed)
{
	auto coinbaseTx = createCoinbase();
	auto lTx = createLicenseTransaction(coinbaseTx.GetHash());

	unsigned char rawAddress[] = {169, 20, 230, 53, 247, 106, 15, 189, 177, 112, 86, 88, 161, 227, 176, 86, 115, 120, 7, 74};
	std::string address(rawAddress, rawAddress + 20);

	minerLicenses.PushLicense(1, 3, address);
	minerLicenses.HandleTx(CTransaction(lTx), 2);
	auto licenses = minerLicenses.GetLicenses();
	BOOST_CHECK_EQUAL(1, licenses.size());
	BOOST_CHECK_EQUAL(5, licenses[0].hashRate);
}

BOOST_AUTO_TEST_CASE(shouldModifyLicenseIfAlreadyExists)
{
	auto coinbaseTx = createCoinbase();
	auto lTx = createLicenseTransaction(coinbaseTx.GetHash());

	minerLicenses.HandleTx(CTransaction(lTx), 1);
	auto licenses = minerLicenses.GetLicenses();
	BOOST_CHECK_EQUAL(5, licenses[0].hashRate);

	lTx.vout[1].scriptPubKey[28] = 3; // modyfing hashrate
	minerLicenses.HandleTx(CTransaction(lTx), 2);
	licenses = minerLicenses.GetLicenses();
	BOOST_CHECK_EQUAL(3, licenses[0].hashRate);
}

BOOST_AUTO_TEST_CASE(shouldNotModifyLicenseIfProvidedOlderEntry)
{
	auto coinbaseTx = createCoinbase();
	auto lTx = createLicenseTransaction(coinbaseTx.GetHash());

	minerLicenses.HandleTx(CTransaction(lTx), 2);
	auto licenses = minerLicenses.GetLicenses();
	BOOST_CHECK_EQUAL(5, licenses[0].hashRate);

	lTx.vout[1].scriptPubKey[28] = 3; // modyfing hashrate
	minerLicenses.HandleTx(CTransaction(lTx), 1);
	licenses = minerLicenses.GetLicenses();
	BOOST_CHECK_EQUAL(5, licenses[0].hashRate);
}

BOOST_AUTO_TEST_CASE(shouldPushLicenseIfNotExists)
{
	minerLicenses.PushLicense(1, 5, "2N23yxpHnHpQvUNWe3Ujk5nxR6YCxeXoRiT");
	auto licenses = minerLicenses.GetLicenses();

	BOOST_CHECK_EQUAL(1, licenses.size());
	BOOST_CHECK_EQUAL(5, licenses[0].hashRate);
}

BOOST_AUTO_TEST_CASE(shouldNotPushLicenseIfAlreadyExists)
{
	minerLicenses.PushLicense(1, 5, "2N23yxpHnHpQvUNWe3Ujk5nxR6YCxeXoRiT");
	minerLicenses.PushLicense(2, 3, "2N23yxpHnHpQvUNWe3Ujk5nxR6YCxeXoRiT");
	auto licenses = minerLicenses.GetLicenses();

	BOOST_CHECK_EQUAL(1, licenses.size());
	BOOST_CHECK_EQUAL(5, licenses[0].hashRate);
}

BOOST_AUTO_TEST_SUITE_END()
