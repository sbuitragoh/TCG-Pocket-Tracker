from src.utils import ensure_row_index, get_set_df
import polars as pl

class InventoryManager:

    def __init__(self, df, inventory):
        self.df = df
        self.inventory = inventory

    def _update_completion(self, df):

        owned_set = ensure_row_index(df).filter(pl.col("row_idx").is_in(list(self.inventory)))
        set_missing = df.height - owned_set.height
        return df.height, owned_set.height, set_missing
    
    def update_completion(self, df: pl.DataFrame, is_set: bool, display_order):

        color = "#1c9625" if is_set else "#2b2ee9"
        df = ensure_row_index(df)

        total_counts = df.group_by('pack').len().rename({'len': 'total'})
        owned_df = df.filter(pl.col("row_idx").is_in(list(self.inventory)))
        owned_counts = owned_df.group_by('pack').len().rename({'len': 'owned'})

        joined = (
            total_counts
            .join(owned_counts, on="pack", how="left")
            .with_columns([
                pl.col("owned").fill_null(0),
                (pl.col("total") - pl.col("owned")).alias("missing")
            ])
            .sort("pack")
        )

        pack_order = {pack:i for i, pack in enumerate(display_order)}
        joined_rows = sorted(
            joined.iter_rows(named=True),
            key=lambda row: pack_order.get(row['pack'], 9999)
        )

        return joined_rows, color
    
    def _update_count(self):

        total, owned = len(self.df), len(self.inventory)
        missing = total - owned

        return total, owned, missing

    def _update_suggestion(self, is_set):

        df = get_set_df(self.df) if is_set else self.df
        df = ensure_row_index(df)
        relevant_indices = set(df["row_idx"].to_list())
        missing_cards = df.filter(
            (~pl.col("row_idx").is_in(self.inventory)) &
            (pl.col("row_idx").is_in(list(relevant_indices))) &
            pl.col("rarity").is_not_null() &
            pl.col("pack").is_not_null()
        )

        return missing_cards
    
    def _get_incomplete_packs(self, is_set):
        
        df = get_set_df(self.df) if is_set else self.df
        df = ensure_row_index(df)

        if "pack" not in df.columns:
            return []
        
        pack_counts = df["pack"].value_counts()
        owned_packs = (
            df
            .filter(pl.col("row_idx").is_in(self.inventory))["pack"]
            .value_counts()
        )

        incomplete_df = (
            pack_counts.join(owned_packs, on='pack', how='left', suffix='_owned')
            .with_columns([
                pl.col('count_owned').fill_null(0).alias('owned'),
                pl.col('count').alias('total')
            ])
            .with_columns([
                (pl.col('total') - pl.col('owned')).alias('missing')
            ])
            .filter(
                (pl.col('pack') != 'Both') &
                (pl.col('missing') > 0)
            )
            .select(['pack', 'owned', 'total', 'missing'])
        )

        incomplete = incomplete_df.rows()

        return incomplete

    def _calculate_pack_probabilities(self, packs, missing_cards, prob_matrix):

        pack_probs = {}

        for pack in packs:

            pack_name = pack[0]
            filtered = missing_cards.filter(
                (pl.col("pack") == pack_name) | (pl.col("pack") == "Both")
            ).select("rarity")
        
            if filtered.height == 0:
                pack_probs[pack_name] = 0.0
            else:
                prob_seted = filtered.with_columns(
                    (pl.col('rarity').replace_strict(prob_matrix)).alias('rar_prob')
                ).with_columns(
                    pl.col('rar_prob').list.to_struct(fields=['P_123', 'P_4', 'P_5'])
                ).unnest('rar_prob').with_columns([(
                    (1 - ((1-pl.col('P_123'))**3 * (1-pl.col('P_4')) * (1-pl.col('P_5'))))
                    .cast(pl.Decimal(precision=20, scale=15))
                    .alias('P')
                )]).select(
                    pl.sum('P')
                ).item()
                pack_probs[pack_name] = float(prob_seted)
        
        return pack_probs

    def _display_pack_suggestion(self, pack_probs) -> str:

        max_prob = max(pack_probs.values())
        best_packs = [p for p, v in pack_probs.items()
                      if abs(v - max_prob) < 1e-8]
        suggestion = ""

        df = ensure_row_index(self.df)
        missing_df = df.filter(~pl.col("row_idx").is_in(list(self.inventory)))
        if missing_df.is_empty():
            suggestion += "You have all cards in your collection.\n"

        if len(best_packs) == 1:
            max_prob = 1 if max_prob > 1 else max_prob 
            if max_prob == 1:
                suggestion += f"Suggestion: Open '{best_packs[0]}' pack.\nIt's more likely to get a new card with it!"
            else:
                suggestion += f"Suggestion: Open '{best_packs[0]}' pack.\nIt has a probability of {max_prob*100:.2f} % to have a new card.\n"
        else:
            suggestion += f"Any pack has the same chance to get you a new card!\n"

        return suggestion
